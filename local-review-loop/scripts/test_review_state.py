#!/usr/bin/env python3
"""review_state.py 测试（只用临时目录）：python3 test_review_state.py"""
import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import review_state as m  # noqa: E402


def report(k, baseline, verdict):
    return f"\n## 第 {k} 轮审核报告\n内容\n\nReviewed-Baseline: {baseline}\nVerdict: {verdict}\n"


def quiet(fn, *args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fn(*args)
    return code, buf.getvalue()


class Pure(unittest.TestCase):
    def test_scope(self):
        self.assertEqual(m.parse_scope("# c\nb.py\n\na.py\nb.py\nsrc\\x.py"), ["a.py", "b.py", "src/x.py"])
        for bad in ("../x.py", "/etc/passwd", "", "# only comment"):
            with self.assertRaises(m.StateError):
                m.parse_scope(bad)

    def test_fingerprint_stable_and_scope_sensitive(self):
        a = m.fingerprint({"b": "2", "a": "1"})
        self.assertEqual(a, m.fingerprint({"a": "1", "b": "2"}))
        self.assertNotEqual(a, m.fingerprint({"a": "1"}))
        self.assertNotEqual(a, m.fingerprint({"a": "1", "b": "MISSING"}))

    def test_parse_reviews(self):
        fp = "a" * 64
        text = ("## 范围与基线\nVerdict: CLEAR 不是报告\n" + report(1, fp, "BLOCKED（建议修 1 项）")
                + "## 第 1 轮处理报告\nx\n" + report(2, fp, "CLEAR"))
        reviews, malformed = m.parse_reviews(text)
        self.assertEqual([r["verdict"] for r in reviews], ["BLOCKED（建议修 1 项）", "CLEAR"])
        self.assertEqual(malformed, [])
        _, malformed = m.parse_reviews(report(3, fp, "CLEAR（附注）"))
        self.assertTrue(malformed[0]["clear_like"])

    def test_assess(self):
        fp = "a" * 64
        ok = m.assess(fp, [], [{"round": 1, "title": "t", "baseline": fp, "verdict": "CLEAR"}], [], True)
        self.assertEqual(ok["blockers"], [])
        stale = m.assess("b" * 64, [], [{"round": 1, "title": "t", "baseline": fp, "verdict": "CLEAR"}], [], True)
        self.assertTrue(any("复审" in b for b in stale["blockers"]))
        bad = m.assess(fp, [], [{"round": 1, "title": "t", "baseline": fp, "verdict": "CLEAR"}],
                       [{"round": 2, "title": "第 2 轮", "clear_like": True}], True)
        self.assertTrue(any("格式不符" in b for b in bad["blockers"]))
        soft = m.assess(fp, [], [{"round": 1, "title": "t", "baseline": fp, "verdict": "CLEAR"}],
                        [{"round": 2, "title": "第 2 轮", "clear_like": False}], True)
        self.assertEqual(soft["blockers"], [])


class Cycle(unittest.TestCase):
    def test_full_cycle(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".review").mkdir()
            (root / "src").mkdir()
            (root / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
            (root / ".review" / "scope.txt").write_text("src/a.py\n", encoding="utf-8")
            code, out = quiet(m.snapshot, root)
            fp1 = out.split("基线指纹：")[1].split("\n")[0]
            (root / ".review" / "REVIEW.md").write_text(report(1, fp1, "BLOCKED（必须修 1 项）"), encoding="utf-8")
            self.assertEqual(quiet(m.status, root, True)[0], 1)

            (root / "src" / "a.py").write_text("x = 2\n", encoding="utf-8")
            code, out = quiet(m.diff, root, None)
            self.assertIn("-x = 1", out)
            self.assertIn("+x = 2", out)
            code, out = quiet(m.snapshot, root)
            fp2 = out.split("基线指纹：")[1].split("\n")[0]
            self.assertNotEqual(fp1, fp2)
            with open(root / ".review" / "REVIEW.md", "a", encoding="utf-8") as f:
                f.write(report(2, fp2, "CLEAR"))
            self.assertEqual(quiet(m.status, root, True)[0], 0)

            (root / "src" / "a.py").write_text("x = 3\n", encoding="utf-8")
            self.assertEqual(quiet(m.status, root, True)[0], 1)

    def test_diff_without_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".review").mkdir()
            (root / "a.py").write_text("x\n", encoding="utf-8")
            (root / ".review" / "scope.txt").write_text("a.py\n", encoding="utf-8")
            (root / ".review" / "REVIEW.md").write_text(report(1, "c" * 64, "CLEAR"), encoding="utf-8")
            with self.assertRaises(m.StateError):
                quiet(m.diff, root, None)


if __name__ == "__main__":
    unittest.main()
