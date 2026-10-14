#!/usr/bin/env python3
"""pr_state.py 纯函数测试（不访问网络）：python3 test_pr_state.py"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pr_state as m  # noqa: E402

SHA_A, SHA_B = "a" * 40, "b" * 40


def report(sha, verdict):
    return f"## 第 1 轮独立审核\n内容\n\nReviewed-Head: {sha}\nVerdict: {verdict}"


def comment(body, t, url=None, updated=None):
    return {"url": url or f"u{t}", "author": "x", "created_at": f"2026-01-01T00:00:{t:02d}Z",
            "updated_at": updated or f"2026-01-01T00:00:{t:02d}Z", "body": body}


OPEN_PR = {"state": "OPEN", "isDraft": False, "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN",
           "headRefOid": SHA_A}
NO_CI = {"status": "none_reported", "checks": []}
RULES_NONE = {"protection": "none", "required_checks": [], "rulesets": [], "merge_queue": False}
NO_WF = {"head": False, "base": False}


def run(comments, pr=None, compare=None, all_checks=NO_CI, req=NO_CI, rules=RULES_NONE, wf=NO_WF):
    return m.assess(pr or OPEN_PR, comments, all_checks, req, rules, wf, compare or (lambda x, y: None))


class ParseVerdict(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(m.parse_verdict(report(SHA_A, "CLEAR"))["verdict"], "CLEAR")
        for v in ("BLOCKED（必须修 1 项）", "BLOCKED（建议修 2 项）", "BLOCKED（必须修 1 项，建议修 3 项）"):
            self.assertEqual(m.parse_verdict(report(SHA_A, v))["verdict"], v)

    def test_invalid(self):
        for v in ("CLEAR（附 2 项）", "clear", "BLOCKED", "BLOCKED（随便）", "BLOCKED (必须修 1 项)",
                  "BLOCKED（必须修 0 项）"):
            self.assertIsNone(m.parse_verdict(report(SHA_A, v)), v)
        self.assertIsNone(m.parse_verdict(f"```\nReviewed-Head: {SHA_A}\nVerdict: CLEAR\n```"))
        self.assertIsNone(m.parse_verdict(report(SHA_A, "CLEAR") + "\n尾随文字"))

    def test_loose(self):
        self.assertTrue(m.looks_like_verdict("x\n**Verdict:** CLEAR"))
        self.assertTrue(m.looks_like_verdict("x\nverdict： clear"))
        self.assertFalse(m.looks_like_verdict("## 第 2 轮处理报告\nVerdict: CLEAR 已收到"))
        self.assertFalse(m.looks_like_verdict("## 仅供参考处置记录\nReviewed-Head: x"))
        self.assertFalse(m.looks_like_verdict("普通评论"))


class Carrier(unittest.TestCase):
    def test_carriers(self):
        for p in ("pr-review-loop/SKILL.md", "AGENTS.md", "x/references/a.md", "conf/app.yaml",
                  ".github/workflows/ci.yml", "src/locales/zh.po"):
            self.assertTrue(m.is_behavior_carrier(p), p)
        for p in ("README.md", "src/app.py", "docs/guide.md"):
            self.assertFalse(m.is_behavior_carrier(p), p)

    def test_protection(self):
        self.assertEqual(m.classify_protection(True, ""), "protected")
        self.assertEqual(m.classify_protection(False, "gh: Branch not protected (HTTP 404)"), "none")
        self.assertEqual(m.classify_protection(False, "gh: Not Found (HTTP 404)"), "unknown")


class Assess(unittest.TestCase):
    def test_clear_bound_no_ci(self):
        out = run([comment(report(SHA_A, "CLEAR"), 1)])
        self.assertEqual(out["mechanical_blockers"], [])
        self.assertEqual(out["checks"]["applicability"], "no_workflows")

    def test_unknown_protection_keeps_ci_blocker(self):
        out = run([comment(report(SHA_A, "CLEAR"), 1)], rules=dict(RULES_NONE, protection="unknown"))
        self.assertEqual(out["checks"]["applicability"], "unknown")
        self.assertTrue(any("未报告任何检查" in b for b in out["mechanical_blockers"]))

    def test_newer_malformed_blocks_older_does_not(self):
        newer = run([comment(report(SHA_A, "CLEAR"), 1), comment("x\nVerdict: CLEAR（附注）", 2)])
        self.assertTrue(any("格式不符" in b for b in newer["mechanical_blockers"]))
        older = run([comment("x\nVerdict: CLEAR（附注）", 1), comment(report(SHA_A, "CLEAR"), 2)])
        self.assertEqual(older["mechanical_blockers"], [])

    def test_handling_report_quote_not_malformed(self):
        out = run([comment(report(SHA_A, "CLEAR"), 1), comment("## 第 1 轮处理报告\nVerdict: CLEAR 引用", 2)])
        self.assertEqual(out["mechanical_blockers"], [])

    def test_edited_latest_blocks(self):
        out = run([comment(report(SHA_A, "CLEAR"), 1, updated="2026-01-02T00:00:00Z")])
        self.assertTrue(any("被编辑" in b for b in out["mechanical_blockers"]))

    def test_exemption_candidate(self):
        cmp = lambda x, y: {"status": "ahead", "ahead_by": 1, "files": [{"filename": "src/app.py"}]}
        out = run([comment(report(SHA_B, "CLEAR"), 1)], compare=cmp)
        self.assertEqual(out["mechanical_blockers"], [])
        self.assertEqual(out["exemption_candidate"]["files"], ["src/app.py"])

    def test_exemption_rejected_for_carrier_or_diverged(self):
        cmp = lambda x, y: {"status": "ahead", "ahead_by": 1, "files": [{"filename": "a/SKILL.md"}]}
        out = run([comment(report(SHA_B, "CLEAR"), 1)], compare=cmp)
        self.assertIsNone(out["exemption_candidate"])
        self.assertTrue(any("行为载体" in b for b in out["mechanical_blockers"]))
        cmp = lambda x, y: {"status": "diverged", "files": [{"filename": "src/app.py"}]}
        out = run([comment(report(SHA_B, "CLEAR"), 1)], compare=cmp)
        self.assertTrue(any("非线性" in b for b in out["mechanical_blockers"]))

    def test_blocked_not_exempt(self):
        out = run([comment(report(SHA_B, "BLOCKED（必须修 1 项）"), 1)],
                  compare=lambda x, y: {"status": "ahead", "files": [{"filename": "src/app.py"}]})
        self.assertIsNone(out["exemption_candidate"])
        self.assertTrue(any("重新审核" in b for b in out["mechanical_blockers"]))

    def test_mergeability(self):
        out = run([comment(report(SHA_A, "CLEAR"), 1)], pr=dict(OPEN_PR, mergeable="UNKNOWN"))
        self.assertTrue(any("UNKNOWN" in b for b in out["mechanical_blockers"]))
        out = run([comment(report(SHA_A, "CLEAR"), 1)], pr=dict(OPEN_PR, mergeStateStatus="BEHIND"))
        self.assertTrue(any("落后" in b for b in out["mechanical_blockers"]))

    def test_failed_checks_and_merge_queue(self):
        checks = {"status": "ok", "checks": [{"name": "t", "bucket": "fail"}]}
        out = run([comment(report(SHA_A, "CLEAR"), 1)], all_checks=checks,
                  rules=dict(RULES_NONE, merge_queue=True, rulesets=["merge_queue"]))
        self.assertTrue(any("fail" in b for b in out["mechanical_blockers"]))
        self.assertTrue(any("合并队列" in x for x in out["needs_manual_check"]))

    def test_skip_ci(self):
        out = m.assess(OPEN_PR, [comment(report(SHA_A, "CLEAR"), 1)], None, None, None, {}, lambda x, y: None)
        self.assertEqual(out["mechanical_blockers"], [])
        self.assertEqual(out["checks"]["applicability"], "skipped")


if __name__ == "__main__":
    unittest.main()
