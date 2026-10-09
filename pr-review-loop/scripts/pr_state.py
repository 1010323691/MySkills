#!/usr/bin/env python3
"""只读汇总 PR 审核闭环所需的门禁事实，供主 Agent / 审核子 Agent 每轮核对。

用法：
    python3 pr_state.py --repo OWNER/REPO --pr 42 [--hostname github.example.com] [--json]

输出（默认人类可读，--json 输出结构化结果）：
- PR 状态：state / draft / mergeable / mergeStateStatus / base / head / 完整 HEAD SHA / 自动合并安排
- 全部审核结论评论（分页读取全部评论，按「末两行 Reviewed-Head + Verdict」识别）
- 最新结论是否绑定当前 HEAD
- CI 检查（全部与 required）按 bucket 汇总
- 可机械判定的阻塞项清单

本脚本只做 gh 读取，不发布、不合并、不改分支。它不能判断审核者是否独立、
发现项是否全部关闭、skipped 检查是否适用——这些仍需人工核对（输出中列为「需人工核对」）。
"""
import argparse
import json
import re
import subprocess
import sys

SHA_RE = re.compile(r"^Reviewed-Head:\s*([0-9a-fA-F]{40})\s*$")
VERDICT_RE = re.compile(r"^Verdict:\s*(CLEAR|BLOCKED.*)$")


def gh(args, hostname=None, check=True):
    cmd = ["gh"] + args
    env = None
    if hostname:
        import os
        env = dict(os.environ, GH_HOST=hostname)
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
              "--jq", ".[] | {url: .html_url, author: .user.login, created_at: .created_at, body: .body}"],
             a.hostname).stdout
    comments = [json.loads(l) for l in raw.splitlines() if l.strip()]
    verdicts = []
    for c in comments:
        v = parse_verdict(c["body"])
        if v:
            verdicts.append({"url": c["url"], "author": c["author"], "created_at": c["created_at"], **v})

    head = (pr.get("headRefOid") or "").lower()
    latest = verdicts[-1] if verdicts else None
    all_checks = read_checks(a.repo, a.pr, a.hostname, required=False)
    req_checks = read_checks(a.repo, a.pr, a.hostname, required=True)

    blockers = []
    if pr.get("state") != "OPEN":
        blockers.append(f"PR 状态为 {pr.get('state')}，不是 OPEN")
    if pr.get("isDraft"):
        blockers.append("PR 仍是 draft")
    if pr.get("mergeable") == "CONFLICTING":
        blockers.append("存在合并冲突")
    if not latest:
        blockers.append("没有任何审核结论评论")
    else:
        if latest["reviewed_head"] != head:
            blockers.append(f"最新结论绑定 {latest['reviewed_head'][:12]}，当前 HEAD 为 {head[:12]}：须对当前 HEAD 重新审核")
        if latest["verdict"] != "CLEAR":
            blockers.append(f"最新结论为 {latest['verdict']}")
    if all_checks["status"] == "none_reported":
        blockers.append("未报告任何检查：不等于通过；须核实是否确实无适用 CI（见 SKILL.md 5.2）")
    elif all_checks["status"] == "error":
        blockers.append(f"读取检查失败：{all_checks.get('detail')}")
    b = summarize(all_checks["checks"])
    for bad in ("fail", "cancel", "pending"):
        if b.get(bad):
            blockers.append(f"检查 {bad}：{', '.join(b[bad])}")
    if pr.get("autoMergeRequest"):
        blockers.append("PR 上存在自动合并安排：须确认它不会绕过本轮版本门禁（见 references/merge-queue.md）")

    manual = [
        "最新结论评论是否确由本轮独立审核子 Agent 发布（同账号时不能只看作者）",
        "全部编号发现项是否已独立核销 / 接受反驳 / 有用户延期裁定",
        "skipped / neutral 检查是否确实不适用；required checks 是否完整出现",
        "仓库是否要求正式 review（reviewDecision）或合并队列",
    ]
    if b.get("skipping"):
        manual.insert(2, f"skipped 检查需核实适用性：{', '.join(b['skipping'])}")

    out = {"pr": pr, "verdicts": verdicts, "latest_verdict": latest,
           "latest_binds_current_head": bool(latest and latest["reviewed_head"] == head),
           "checks": {"all": all_checks, "required": req_checks, "by_bucket": b},
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
        mark = "← 当前 HEAD" if v["reviewed_head"] == head else ""
        print(f"  {v['created_at']} {v['verdict']} @ {v['reviewed_head'][:12]} by {v['author']} {v['url']} {mark}")
    print(f"检查（全部）：{all_checks['status']} {json.dumps(b, ensure_ascii=False)}")
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
