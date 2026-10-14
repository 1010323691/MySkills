#!/usr/bin/env python3
"""只读汇总 PR 审核闭环所需的门禁事实，供主 Agent / 审核子 Agent 核对。

用法：
    # 门禁 / 恢复 / 审核前核对
    python3 pr_state.py --repo OWNER/REPO --pr 42 [--json] [--strict] [--skip-ci] [--dump-comments latest|all]
    # 第 0 节：PR 创建前的仓库事实（base 保护、rulesets、合并队列、workflows、允许的合并方式）
    python3 pr_state.py --repo OWNER/REPO --repo-facts --base main [--json]
    # 有界等待 CI（先等检查注册，再等结果），后台运行
    python3 pr_state.py --repo OWNER/REPO --pr 42 --wait-ci 30

通用参数：--hostname <GitHub Enterprise 主机名>（默认 github.com）。

门禁模式输出：
- PR 状态、完整 HEAD SHA、可合并性（mergeable / mergeStateStatus）、自动合并安排
- 全部审核结论（评论末两行 Reviewed-Head + Verdict）；格式不符的疑似结论、发布后被编辑的最新结论列为阻塞项
- 最新 CLEAR 未绑定当前 HEAD 但线性追加时，列为「文案豁免候选」并给出改动文件与疑似行为载体
- CI 检查按 bucket 汇总与适用性；base 保护 / rulesets / 合并队列
- 可机械判定的阻塞项与需人工核对项
--strict 退出码：0 无阻塞；1 有阻塞项；4 无阻塞项但有待人工核对的文案豁免候选。
--wait-ci 退出码：0 检查全部结束且无失败；1 有 fail/cancel；3 宽限期内一直没有检查注册；8 到时仍 pending；2 读取出错。

本脚本只做 gh 读取，不发布、不合并、不改分支。它不能判断审核者是否独立、
发现项是否全部关闭、skipped 检查是否适用——这些仍需人工核对。
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from urllib.parse import quote

SHA_RE = re.compile(r"^Reviewed-Head:\s*([0-9a-fA-F]{40})\s*$")
VERDICT_RE = re.compile(
    r"^Verdict:\s*(CLEAR|BLOCKED（(?:必须修 [1-9]\d* 项(?:，建议修 [1-9]\d* 项)?|建议修 [1-9]\d* 项)）)$")
# 行首像结论行（容忍大小写、全角冒号、Markdown 修饰）——用于发现格式不符、会被静默忽略的结论
LOOSE_RE = re.compile(r"^[\s>*_`#-]*(Verdict|Reviewed-Head)\s*[:：]", re.IGNORECASE)
# 主 Agent 发布的非结论评论（处理报告、处置记录、状态评论）：其中引用的结论行不算疑似结论
NON_VERDICT_HEAD_RE = re.compile(r"^##\s*(第\s*\d+\s*轮处理报告|仅供参考处置记录|闭环状态)")
# 疑似行为载体：文案豁免不适用（见 SKILL.md 2.1 / 第 3 节）
CARRIER_NAMES = {"SKILL.md", "AGENTS.md", "CLAUDE.md"}
CARRIER_EXTS = (".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env", ".lock", ".po", ".properties")
CARRIER_DIRS = ("references/", "prompts/", "locales/", "locale/", "i18n/", ".github/")


def gh(args, hostname=None, check=True):
    cmd = ["gh"] + args
    env = dict(os.environ, GH_HOST=hostname) if hostname else None
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env)
    if check and p.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} 失败（{p.returncode}）：{p.stderr.strip()}")
    return p


def gh_json(args, hostname):
    """返回 (ok, data, stderr)。"""
    p = gh(args, hostname, check=False)
    if p.returncode != 0:
        return False, None, (p.stderr or p.stdout or "").strip()
    try:
        return True, json.loads(p.stdout or "null"), ""
    except ValueError:
        return False, None, "无法解析 JSON 输出"


# ---------- 纯函数（无 IO，供测试） ----------

def _lines(body):
    return [l.strip() for l in (body or "").replace("\r\n", "\n").split("\n") if l.strip()]


def parse_verdict(body):
    """仅当评论末两行非空行依次为 Reviewed-Head / Verdict 时视为审核结论。"""
    lines = _lines(body)
    if len(lines) < 2:
        return None
    m_sha, m_v = SHA_RE.match(lines[-2]), VERDICT_RE.match(lines[-1])
    if not (m_sha and m_v):
        return None
    return {"reviewed_head": m_sha.group(1).lower(), "verdict": m_v.group(1)}


def looks_like_verdict(body):
    lines = (body or "").replace("\r\n", "\n").split("\n")
    first = next((l.strip() for l in lines if l.strip()), "")
    if NON_VERDICT_HEAD_RE.match(first):
        return False
    return any(LOOSE_RE.match(l) for l in lines)


def is_behavior_carrier(path):
    name = path.rsplit("/", 1)[-1]
    return (name in CARRIER_NAMES or name.lower().endswith(CARRIER_EXTS)
            or any(d in "/" + path for d in ("/" + x for x in CARRIER_DIRS)))


def summarize(checks):
    s = {}
    for c in checks:
        s.setdefault(c.get("bucket", "unknown"), []).append(c.get("name"))
    return s


def classify_protection(ok, stderr):
    """分支保护接口：200 = protected；404 且消息为 Branch not protected = none；其余（Not Found/403）= unknown。"""
    if ok:
        return "protected"
    return "none" if "Branch not protected" in (stderr or "") else "unknown"


def assess(pr, comments, all_checks, req_checks, rules, workflows, compare_fn):
    """由已取得的事实计算结论、阻塞项与人工核对项。compare_fn(base_sha, head_sha) -> dict|None。"""
    head = (pr.get("headRefOid") or "").lower()
    verdicts, malformed = [], []
    for c in comments:
        v = parse_verdict(c.get("body"))
        if v:
            verdicts.append({"url": c["url"], "author": c.get("author"), "created_at": c["created_at"],
                             "edited": bool(c.get("updated_at")) and c.get("updated_at") != c["created_at"], **v})
        elif looks_like_verdict(c.get("body")):
            malformed.append({"url": c["url"], "created_at": c["created_at"]})
    latest = verdicts[-1] if verdicts else None
    blockers, manual = [], []

    if pr.get("state") != "OPEN":
        blockers.append(f"PR 状态为 {pr.get('state')}，不是 OPEN")
    else:
        if pr.get("isDraft"):
            blockers.append("PR 仍是 draft")
        mergeable, mss = pr.get("mergeable"), pr.get("mergeStateStatus")
        if mergeable == "CONFLICTING" or mss == "DIRTY":
            blockers.append("存在合并冲突")
        elif mergeable == "UNKNOWN" or mss == "UNKNOWN":
            blockers.append("GitHub 尚未算出可合并性（UNKNOWN）：稍后重跑本脚本")
        if mss == "BEHIND":
            blockers.append("head 落后 base 且仓库要求先更新：更新分支会产生新 HEAD，须重新审核")
        elif mss == "BLOCKED":
            blockers.append("仓库保护阻塞合并（正式 review / required checks / 其他规则）：对照 reviewDecision 与 required checks")
    if pr.get("autoMergeRequest"):
        blockers.append("PR 上存在自动合并安排：须确认它不会绕过本轮版本门禁（见 references/merge-queue.md）")

    # 只有晚于最新有效结论的格式错误评论会影响门禁；更早的已被取代
    for m in malformed:
        if not latest or m["created_at"] > latest["created_at"]:
            blockers.append(f"疑似审核结论但末两行格式不符（会被忽略）：{m['url']}；由审核者发新的完整报告")
        else:
            manual.append(f"早于最新结论的格式不符疑似结论（已被取代）：{m['url']}")

    exemption = None
    if not latest:
        blockers.append("没有任何审核结论评论")
    else:
        if latest["edited"]:
            blockers.append(f"最新结论评论发布后被编辑过：{latest['url']}；起新审核者复核")
        if latest["verdict"] != "CLEAR":
            blockers.append(f"最新结论为 {latest['verdict']}")
        if latest["reviewed_head"] != head:
            unbound = f"最新结论绑定 {latest['reviewed_head'][:12]}，当前 HEAD 为 {head[:12]}：须对当前 HEAD 重新审核"
            cmp = compare_fn(latest["reviewed_head"], head) if latest["verdict"] == "CLEAR" and head else None
            files = [f["filename"] for f in (cmp or {}).get("files") or []]
            carriers = [f for f in files if is_behavior_carrier(f)]
            if cmp and cmp.get("status") == "ahead" and files and not carriers:
                exemption = {"reviewed_head": latest["reviewed_head"], "head": head,
                             "ahead_by": cmp.get("ahead_by"), "files": files}
            else:
                if cmp and cmp.get("status") != "ahead":
                    unbound += f"（CLEAR 后非线性追加：{cmp.get('status')}，文案豁免不适用）"
                elif carriers:
                    unbound += f"（CLEAR 后改动含疑似行为载体：{', '.join(carriers)}，文案豁免不适用）"
                blockers.append(unbound)

    ci = {"all": all_checks, "required": req_checks, "by_bucket": {}, "applicability": "skipped"}
    if all_checks is not None:
        b = summarize(all_checks["checks"])
        ci["by_bucket"] = b
        ci["applicability"] = "checks_reported"
        if all_checks["status"] == "none_reported":
            no_required_rules = (rules is not None and rules.get("protection") in ("none", "protected")
                                 and not rules.get("required_checks") and rules.get("rulesets") is not None
                                 and "required_status_checks" not in rules["rulesets"])
            if (workflows.get("head") is False and workflows.get("base") is False
                    and req_checks and req_checks["status"] == "none_reported" and no_required_rules):
                ci["applicability"] = "no_workflows"
                manual.append("未报告任何检查，base/head 均无 .github/workflows，保护与 rulesets 均无 required checks："
                              "可记录 CI 不适用（仓库若依赖外部 CI 或第三方状态检查，仍须人工确认）")
            else:
                ci["applicability"] = "unknown"
                blockers.append(f"未报告任何检查（workflows：head={workflows.get('head')} base={workflows.get('base')}；"
                                f"保护={(rules or {}).get('protection')}）：不等于通过；刚推送时用 --wait-ci 等注册，"
                                "仍为空按 SKILL.md 5.2 核实")
        elif all_checks["status"] == "error":
            blockers.append(f"读取检查失败：{all_checks.get('detail')}")
        for bad in ("fail", "cancel", "pending"):
            if b.get(bad):
                blockers.append(f"检查 {bad}：{', '.join(b[bad])}")
        if b.get("skipping"):
            manual.append(f"skipped 检查需核实适用性：{', '.join(b['skipping'])}")
    if rules is not None:
        if rules.get("merge_queue"):
            manual.append("base 启用了合并队列：执行 gh pr merge 之前先读 references/merge-queue.md")
        if rules.get("protection") == "unknown" or rules.get("rulesets") is None:
            manual.append("无法读取 base 分支保护或 rulesets（可能无权限）：required checks / reviews 须人工核实")

    if exemption:
        manual.append(f"文案豁免候选：CLEAR 后线性追加 {exemption['ahead_by']} 个提交，改动文件 "
                      f"{', '.join(exemption['files'])}；逐项核对 SKILL.md 第 3 节五项条件（git diff "
                      f"{exemption['reviewed_head'][:12]}..{exemption['head'][:12]}），不满足则对当前 HEAD 重新审核")
    manual += [
        "最新结论评论是否确由独立审核子 Agent 发布、满足 SKILL.md 2.1 可信条件（同账号时不能只看作者）",
        "必须修 / 建议修是否已独立核销 / 接受反驳 / 有用户裁定；仅供参考是否逐项留痕",
        "skipped / neutral 检查是否确实不适用；required checks 是否完整出现",
        "仓库是否要求正式 review（reviewDecision）",
    ]
    return {"pr": pr, "verdicts": verdicts, "malformed_verdict_comments": malformed, "latest_verdict": latest,
            "latest_binds_current_head": bool(latest and latest["reviewed_head"] == head),
            "exemption_candidate": exemption, "checks": ci, "base_rules": rules,
            "mechanical_blockers": blockers, "needs_manual_check": manual}


# ---------- IO ----------

def read_checks(repo, pr, hostname, required):
    args = ["pr", "checks", str(pr), "--repo", repo, "--json", "name,state,bucket,workflow,link"]
    if required:
        args.append("--required")
    p = gh(args, hostname, check=False)
    # 带 --json 时有失败检查也可能返回 0；只看输出，不从退出码推断结果
    if p.returncode in (0, 1, 8) and p.stdout.strip():
        try:
            checks = json.loads(p.stdout)
        except ValueError:
            checks = None
        if checks:
            return {"status": "ok", "checks": checks}
        if checks == []:
            return {"status": "none_reported", "checks": [], "detail": "检查列表为空"}
    err = (p.stderr or p.stdout).strip()
    if "no checks reported" in err or "no required checks reported" in err:
        return {"status": "none_reported", "checks": [], "detail": err}
    return {"status": "error", "checks": [], "detail": err}


def has_workflows(repo, ref, hostname):
    """ref 上是否存在 .github/workflows：True / False / None（无法判断）。"""
    if not ref:
        return None
    ok, data, err = gh_json(["api", f"repos/{repo}/contents/.github/workflows?ref={quote(ref, safe='')}"], hostname)
    if ok:
        return bool(data)
    return False if "404" in err else None


def read_rules(repo, base, hostname):
    ok, data, err = gh_json(["api", f"repos/{repo}/branches/{quote(base, safe='')}/protection"], hostname)
    protection = classify_protection(ok, err)
    required = []
    requires_review = None
    if ok and data:
        required = ((data.get("required_status_checks") or {}).get("contexts")) or []
        requires_review = bool(data.get("required_pull_request_reviews"))
    ok_r, data_r, _ = gh_json(["api", f"repos/{repo}/rules/branches/{quote(base, safe='')}"], hostname)
    rulesets = [r.get("type") for r in data_r] if ok_r and isinstance(data_r, list) else None
    return {"base": base, "protection": protection, "required_checks": required,
            "requires_review": requires_review, "rulesets": rulesets,
            "merge_queue": (None if rulesets is None else "merge_queue" in rulesets)}


def compare(repo, base_sha, head_sha, hostname):
    ok, data, _ = gh_json(["api", f"repos/{repo}/compare/{base_sha}...{head_sha}", "--jq",
                           "{status: .status, ahead_by: .ahead_by, behind_by: .behind_by, "
                           "files: [.files[]? | {filename, status, additions, deletions}]}"], hostname)
    return data if ok else None


def read_comments(repo, pr, hostname):
    raw = gh(["api", "--paginate", f"repos/{repo}/issues/{pr}/comments",
              "--jq", ".[] | {url: .html_url, author: .user.login, created_at: .created_at, "
                      "updated_at: .updated_at, body: .body}"], hostname).stdout
    return [json.loads(l) for l in raw.splitlines() if l.strip()]


def repo_facts(a):
    ok, meta, err = gh_json(["api", f"repos/{a.repo}", "--jq",
                             "{default_branch, allow_squash_merge, allow_merge_commit, allow_rebase_merge, "
                             "delete_branch_on_merge}"], a.hostname)
    if not ok:
        raise RuntimeError(f"读取仓库信息失败：{err}")
    base = a.base or meta["default_branch"]
    rules = read_rules(a.repo, base, a.hostname)
    keys = (("squash", "allow_squash_merge"), ("merge", "allow_merge_commit"), ("rebase", "allow_rebase_merge"))
    # 无权限时这些字段为 null：记为未知，不能当作「不允许」
    methods = None if all(meta.get(k) is None for _, k in keys) else [m for m, k in keys if meta.get(k)]
    out = {"repo": a.repo, "default_branch": meta["default_branch"], "base_rules": rules,
           "base_has_workflows": has_workflows(a.repo, base, a.hostname),
           "allowed_merge_methods": methods, "delete_branch_on_merge": meta.get("delete_branch_on_merge")}
    if a.json:
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0
    print(f"仓库 {a.repo}（默认分支 {meta['default_branch']}）base={base}")
    print(f"  分支保护：{rules['protection']} required_checks={rules['required_checks']} "
          f"requires_review={rules['requires_review']}")
    print(f"  rulesets：{rules['rulesets']} 合并队列：{rules['merge_queue']}")
    print(f"  base 上 .github/workflows：{out['base_has_workflows']}（head 上请看本地工作区）")
    print(f"  允许的合并方式（按 squash > merge > rebase 优先级）：{methods} "
          f"delete_branch_on_merge={meta.get('delete_branch_on_merge')}"
          + ("（无权限读取，合并方式按项目约定或合并历史判断）" if methods is None else ""))
    return 0


def wait_ci(a):
    start, grace, limit = time.time(), 120, a.wait_ci * 60
    while True:
        r = read_checks(a.repo, a.pr, a.hostname, required=False)
        elapsed = time.time() - start
        if r["status"] == "ok" and r["checks"]:
            b = summarize(r["checks"])
            if b.get("fail") or b.get("cancel"):
                print(f"检查失败：{json.dumps(b, ensure_ascii=False)}")
                return 1
            if not b.get("pending"):
                print(f"检查全部结束：{json.dumps(b, ensure_ascii=False)}（skipped 仍须核实适用性）")
                return 0
        elif r["status"] == "none_reported":
            if elapsed > min(grace, limit):
                print(f"{int(elapsed)} 秒内没有检查注册：按 SKILL.md 5.2 核实 CI 适用性")
                return 3
        else:
            print(f"读取检查出错：{r.get('detail')}")
            return 2
        if elapsed > limit:
            print(f"等待 {a.wait_ci} 分钟仍 pending：{json.dumps(summarize(r['checks']), ensure_ascii=False)}")
            return 8
        time.sleep(30)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, help="OWNER/REPO")
    ap.add_argument("--pr", type=int)
    ap.add_argument("--hostname", help="GitHub Enterprise 主机名（默认 github.com）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--strict", action="store_true", help="有阻塞项时退出码 1，仅有文案豁免候选时 4")
    ap.add_argument("--skip-ci", action="store_true", help="不读取 CI、workflows 与分支规则（审核者用）")
    ap.add_argument("--dump-comments", choices=("latest", "all"),
                    help="附带评论正文：latest = 最新有效结论及其后的评论；all = 全部")
    ap.add_argument("--repo-facts", action="store_true", help="输出仓库与 base 规则事实（不需要 --pr）")
    ap.add_argument("--base", help="--repo-facts 的 base 分支（默认仓库默认分支）")
    ap.add_argument("--wait-ci", type=int, metavar="MINUTES", help="有界等待 CI，总时长上限（分钟）")
    a = ap.parse_args()

    if a.repo_facts:
        return repo_facts(a)
    if a.pr is None:
        ap.error("需要 --pr（--repo-facts 模式除外）")
    if a.wait_ci:
        return wait_ci(a)

    fields = ("number,url,state,isDraft,mergeable,mergeStateStatus,reviewDecision,baseRefName,"
              "headRefName,headRefOid,isCrossRepository,mergedAt,mergeCommit,autoMergeRequest")
    pr = json.loads(gh(["pr", "view", str(a.pr), "--repo", a.repo, "--json", fields], a.hostname).stdout)
    comments = read_comments(a.repo, a.pr, a.hostname)
    head = (pr.get("headRefOid") or "").lower()
    if a.skip_ci:
        all_checks = req_checks = rules = None
        workflows = {}
    else:
        all_checks = read_checks(a.repo, a.pr, a.hostname, required=False)
        req_checks = read_checks(a.repo, a.pr, a.hostname, required=True)
        rules = read_rules(a.repo, pr.get("baseRefName") or "", a.hostname)
        workflows = {}
        if all_checks["status"] == "none_reported":
            workflows = {"head": has_workflows(a.repo, head, a.hostname),
                         "base": has_workflows(a.repo, pr.get("baseRefName"), a.hostname)}
    out = assess(pr, comments, all_checks, req_checks, rules, workflows,
                 lambda x, y: compare(a.repo, x, y, a.hostname))

    dump = []
    if a.dump_comments:
        start = 0
        if a.dump_comments == "latest" and out["latest_verdict"]:
            start = next(i for i, c in enumerate(comments) if c["url"] == out["latest_verdict"]["url"])
        dump = comments[start:]
        out["comments"] = dump

    code = 0
    if a.strict:
        code = 1 if out["mechanical_blockers"] else (4 if out["exemption_candidate"] else 0)
    if a.json:
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return code

    print(f"PR #{pr['number']} {pr['url']}")
    print(f"  state={pr['state']} draft={pr['isDraft']} mergeable={pr['mergeable']} "
          f"mergeStateStatus={pr['mergeStateStatus']} reviewDecision={pr.get('reviewDecision') or '-'}")
    print(f"  base={pr['baseRefName']} head={pr['headRefName']} HEAD={head}")
    if pr.get("mergedAt"):
        print(f"  mergedAt={pr['mergedAt']} mergeCommit={(pr.get('mergeCommit') or {}).get('oid')}")
    print(f"审核结论评论：{len(out['verdicts'])} 条（评论总数 {len(comments)}）")
    for v in out["verdicts"]:
        mark = ("← 当前 HEAD" if v["reviewed_head"] == head else "") + ("（已编辑）" if v["edited"] else "")
        print(f"  {v['created_at']} {v['verdict']} @ {v['reviewed_head'][:12]} by {v['author']} {v['url']} {mark}")
    for m in out["malformed_verdict_comments"]:
        print(f"  ! {m['created_at']} 格式不符的疑似结论：{m['url']}")
    ci = out["checks"]
    if a.skip_ci:
        print("检查：已跳过（--skip-ci）")
    else:
        print(f"检查（全部）：{ci['all']['status']} {json.dumps(ci['by_bucket'], ensure_ascii=False)} "
              f"适用性={ci['applicability']}")
        print(f"检查（required）：{ci['required']['status']} "
              f"{json.dumps(summarize(ci['required']['checks']), ensure_ascii=False)}")
        r = out["base_rules"]
        print(f"base 规则：保护={r['protection']} rulesets={r['rulesets']} 合并队列={r['merge_queue']}")
    print("可机械判定的阻塞项：" + ("无" if not out["mechanical_blockers"] else ""))
    for x in out["mechanical_blockers"]:
        print(f"  - {x}")
    print("需人工核对：")
    for x in out["needs_manual_check"]:
        print(f"  - {x}")
    if dump:
        print(f"\n===== 评论正文（{a.dump_comments}，{len(dump)} 条）=====")
        for c in dump:
            print(f"\n----- {c['created_at']} {c['author']} {c['url']}\n{c['body']}")
    return code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(2)
