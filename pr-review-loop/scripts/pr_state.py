#!/usr/bin/env python3
"""只读汇总 PR 审核闭环所需的门禁事实，供主 Agent / 审核子 Agent 每轮核对。

用法：
    python3 pr_state.py --repo OWNER/REPO --pr 42 [--hostname github.example.com] [--json]

输出（默认人类可读，--json 输出结构化结果）：
- PR 状态：state / draft / mergeable / mergeStateStatus / base / head / 完整 HEAD SHA / 自动合并安排
- 全部审核结论评论（分页读取全部评论，按「末两行 Reviewed-Head + Verdict」识别）；
  格式不符的疑似结论、发布后被编辑过的最新结论都列为阻塞项
- 最新结论是否绑定当前 HEAD；最新 CLEAR 未绑定时列出 CLEAR 之后改动的文件，供核对文案豁免
- CI 检查（全部与 required）按 bucket 汇总；未报告任何检查时核对 base/head 是否有 .github/workflows
- 可机械判定的阻塞项清单（含 mergeable / mergeStateStatus）

本脚本只做 gh 读取，不发布、不合并、不改分支。它不能判断审核者是否独立、
发现项是否全部关闭、skipped 检查是否适用——这些仍需人工核对（输出中列为「需人工核对」）。
"""
import argparse
import json
import os
import re
import subprocess
import sys
from urllib.parse import quote

SHA_RE = re.compile(r"^Reviewed-Head:\s*([0-9a-fA-F]{40})\s*$")
VERDICT_RE = re.compile(r"^Verdict:\s*(CLEAR|BLOCKED（.+）)$")
# 行首像结论行（容忍大小写、全角冒号、Markdown 修饰）——用于发现格式不符、会被静默忽略的结论
LOOSE_RE = re.compile(r"^[\s>*_`#-]*(Verdict|Reviewed-Head)\s*[:：]", re.IGNORECASE)


def gh(args, hostname=None, check=True):
    cmd = ["gh"] + args
    env = dict(os.environ, GH_HOST=hostname) if hostname else None
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env)
    if check and p.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} 失败（{p.returncode}）：{p.stderr.strip()}")
    return p


def parse_verdict(body):
    """仅当评论末两行非空行依次为 Reviewed-Head / Verdict 时视为审核结论。"""
    lines = [l.strip() for l in (body or "").replace("\r\n", "\n").split("\n") if l.strip()]
    if len(lines) < 2:
        return None
    m_sha, m_v = SHA_RE.match(lines[-2]), VERDICT_RE.match(lines[-1])
    if not (m_sha and m_v):
        return None
    return {"reviewed_head": m_sha.group(1).lower(), "verdict": m_v.group(1)}


def looks_like_verdict(body):
    return any(LOOSE_RE.match(l) for l in (body or "").replace("\r\n", "\n").split("\n"))


def has_workflows(repo, ref, hostname):
    """ref 上是否存在 .github/workflows：True / False / None（无法判断）。"""
    p = gh(["api", f"repos/{repo}/contents/.github/workflows?ref={quote(ref, safe='')}"], hostname, check=False)
    if p.returncode == 0:
        try:
            return bool(json.loads(p.stdout))
        except ValueError:
            return None
    return False if "404" in (p.stderr or "") else None


def compare(repo, base_sha, head_sha, hostname):
    """base_sha...head_sha 的线性关系与改动文件；失败返回 None。"""
    p = gh(["api", f"repos/{repo}/compare/{base_sha}...{head_sha}", "--jq",
            "{status: .status, ahead_by: .ahead_by, behind_by: .behind_by, "
            "files: [.files[]? | {filename, status, additions, deletions}]}"], hostname, check=False)
    if p.returncode != 0:
        return None
    try:
        return json.loads(p.stdout)
    except ValueError:
        return None


def read_checks(repo, pr, hostname, required):
    args = ["pr", "checks", str(pr), "--repo", repo, "--json", "name,state,bucket,workflow,link"]
    if required:
        args.append("--required")
    p = gh(args, hostname, check=False)
    # 退出码 8 = 有 pending；输出仍是有效 JSON
    if p.returncode in (0, 8) and p.stdout.strip():
        return {"status": "ok", "checks": json.loads(p.stdout)}
    err = (p.stderr or p.stdout).strip()
    if "no checks reported" in err or "no required checks reported" in err:
        return {"status": "none_reported", "checks": [], "detail": err}
    return {"status": "error", "checks": [], "detail": err}


def summarize(checks):
    s = {}
    for c in checks:
        s.setdefault(c.get("bucket", "unknown"), []).append(c.get("name"))
    return s


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, help="OWNER/REPO")
    ap.add_argument("--pr", required=True, type=int)
    ap.add_argument("--hostname", help="GitHub Enterprise 主机名（默认 github.com）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    a = ap.parse_args()

    fields = ("number,url,state,isDraft,mergeable,mergeStateStatus,reviewDecision,baseRefName,"
              "headRefName,headRefOid,isCrossRepository,mergedAt,mergeCommit,autoMergeRequest")
    pr = json.loads(gh(["pr", "view", str(a.pr), "--repo", a.repo, "--json", fields], a.hostname).stdout)

    # 分页读取全部 issue 评论（审核/处理报告都以普通 PR 评论发布）
    raw = gh(["api", "--paginate", f"repos/{a.repo}/issues/{a.pr}/comments",
              "--jq", ".[] | {url: .html_url, author: .user.login, created_at: .created_at, "
                      "updated_at: .updated_at, body: .body}"],
             a.hostname).stdout
    comments = [json.loads(l) for l in raw.splitlines() if l.strip()]
    verdicts, malformed = [], []
    for c in comments:
        v = parse_verdict(c["body"])
        if v:
            verdicts.append({"url": c["url"], "author": c["author"], "created_at": c["created_at"],
                             "edited": c.get("updated_at") != c["created_at"], **v})
        elif looks_like_verdict(c["body"]):
            malformed.append({"url": c["url"], "created_at": c["created_at"]})

    head = (pr.get("headRefOid") or "").lower()
    latest = verdicts[-1] if verdicts else None
    all_checks = read_checks(a.repo, a.pr, a.hostname, required=False)
    req_checks = read_checks(a.repo, a.pr, a.hostname, required=True)

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
    # 只有晚于最新有效结论的格式错误评论会影响门禁；更早的已被取代，仅列入人工核对
    for m in malformed:
        if not latest or m["created_at"] > latest["created_at"]:
            blockers.append(f"疑似审核结论但末两行格式不符（会被忽略）：{m['url']}；须核实，必要时由审核者发新的完整报告")
        else:
            manual.append(f"早于最新结论的格式不符疑似结论（已被取代）：{m['url']}")
    since_clear = None
    if not latest:
        blockers.append("没有任何审核结论评论")
    else:
        if latest["edited"]:
            blockers.append(f"最新结论评论发布后被编辑过：{latest['url']}；须核实编辑内容，或起新审核者复核")
        if latest["reviewed_head"] != head:
            blockers.append(f"最新结论绑定 {latest['reviewed_head'][:12]}，当前 HEAD 为 {head[:12]}：须对当前 HEAD 重新审核")
            if latest["verdict"] == "CLEAR" and head:
                since_clear = compare(a.repo, latest["reviewed_head"], head, a.hostname)
                if since_clear is None:
                    manual.append("无法读取 CLEAR 之后的改动：文案豁免无法核对，按常规复审")
                elif since_clear.get("status") != "ahead":
                    manual.append(f"CLEAR 之后不是线性追加（compare status={since_clear.get('status')}）：文案豁免不适用")
                else:
                    files = ", ".join(f["filename"] for f in since_clear.get("files") or [])
                    manual.append(f"仅当 CLEAR 后改动全部满足 SKILL.md 第 3 节文案豁免条件时可沿用该 CLEAR；"
                                  f"CLEAR 后改动文件：{files or '（无）'}")
        if latest["verdict"] != "CLEAR":
            blockers.append(f"最新结论为 {latest['verdict']}")
    ci_applicability = "checks_reported"
    if all_checks["status"] == "none_reported":
        wf_head = has_workflows(a.repo, head, a.hostname) if head else None
        wf_base = has_workflows(a.repo, pr.get("baseRefName") or "", a.hostname)
        if wf_head is False and wf_base is False and req_checks["status"] == "none_reported":
            ci_applicability = "no_workflows"
            manual.append("未报告任何检查，base/head 均无 .github/workflows，也无 required checks：可记录 CI 不适用"
                          "（仓库若依赖外部 CI 或第三方状态检查，仍须人工确认）")
        else:
            ci_applicability = "unknown"
            blockers.append(f"未报告任何检查（workflows：head={wf_head} base={wf_base}）：不等于通过；"
                            "刚推送时稍候再查，仍为空按 SKILL.md 5.2 核实")
    elif all_checks["status"] == "error":
        blockers.append(f"读取检查失败：{all_checks.get('detail')}")
    b = summarize(all_checks["checks"])
    for bad in ("fail", "cancel", "pending"):
        if b.get(bad):
            blockers.append(f"检查 {bad}：{', '.join(b[bad])}")
    if pr.get("autoMergeRequest"):
        blockers.append("PR 上存在自动合并安排：须确认它不会绕过本轮版本门禁（见 references/merge-queue.md）")

    if b.get("skipping"):
        manual.append(f"skipped 检查需核实适用性：{', '.join(b['skipping'])}")
    manual += [
        "最新结论评论是否确由本轮独立审核子 Agent 发布（同账号时不能只看作者）",
        "必须修 / 建议修是否已独立核销 / 接受反驳 / 有用户延期裁定；仅供参考是否逐项留痕",
        "skipped / neutral 检查是否确实不适用；required checks 是否完整出现",
        "仓库是否要求正式 review（reviewDecision）或合并队列",
    ]

    out = {"pr": pr, "verdicts": verdicts, "malformed_verdict_comments": malformed, "latest_verdict": latest,
           "latest_binds_current_head": bool(latest and latest["reviewed_head"] == head),
           "since_latest_clear": since_clear,
           "checks": {"all": all_checks, "required": req_checks, "by_bucket": b,
                      "applicability": ci_applicability},
           "mechanical_blockers": blockers, "needs_manual_check": manual}
    if a.json:
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return

    print(f"PR #{pr['number']} {pr['url']}")
    print(f"  state={pr['state']} draft={pr['isDraft']} mergeable={pr['mergeable']} "
          f"mergeStateStatus={pr['mergeStateStatus']} reviewDecision={pr.get('reviewDecision') or '-'}")
    print(f"  base={pr['baseRefName']} head={pr['headRefName']} HEAD={head}")
    if pr.get("mergedAt"):
        print(f"  mergedAt={pr['mergedAt']} mergeCommit={(pr.get('mergeCommit') or {}).get('oid')}")
    print(f"审核结论评论：{len(verdicts)} 条（评论总数 {len(comments)}）")
    for v in verdicts:
        mark = ("← 当前 HEAD" if v["reviewed_head"] == head else "") + ("（已编辑）" if v["edited"] else "")
        print(f"  {v['created_at']} {v['verdict']} @ {v['reviewed_head'][:12]} by {v['author']} {v['url']} {mark}")
    for m in malformed:
        print(f"  ! {m['created_at']} 格式不符的疑似结论：{m['url']}")
    print(f"检查（全部）：{all_checks['status']} {json.dumps(b, ensure_ascii=False)} 适用性={ci_applicability}")
    print(f"检查（required）：{req_checks['status']} {json.dumps(summarize(req_checks['checks']), ensure_ascii=False)}")
    print("可机械判定的阻塞项：" + ("无" if not blockers else ""))
    for x in blockers:
        print(f"  - {x}")
    print("需人工核对：")
    for x in manual:
        print(f"  - {x}")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(2)
