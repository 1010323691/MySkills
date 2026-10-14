#!/usr/bin/env python3
"""本地审核闭环的机械事实：基线指纹、快照、增量 diff、结论绑定。只读被审文件，只写 .review/。

用法（--root 默认当前目录；被审文件清单为 <root>/.review/scope.txt，每行一个相对路径，# 开头为注释）：
    python3 review_state.py snapshot          # 计算基线指纹，把被审文件快照到 .review/snapshots/<指纹>/
    python3 review_state.py status [--strict] # 当前指纹、REVIEW.md 全部结论及绑定、阻塞项
    python3 review_state.py diff [--from <指纹>]  # 从最新审核报告的基线快照（或指定指纹）到当前文件的统一 diff

基线指纹算法（固定）：对清单内每个文件取 sha256(文件字节)，缺失文件记为 MISSING；
按路径升序逐行拼接「路径<TAB>哈希\\n」，UTF-8 编码后整体取 sha256。清单变化也会改变指纹。
--strict 退出码：0 无阻塞；1 有阻塞项。其他错误退出码 2。
"""
import argparse
import difflib
import hashlib
import re
import shutil
import sys
from pathlib import Path, PurePosixPath

BASELINE_RE = re.compile(r"^Reviewed-Baseline:\s*([0-9a-fA-F]{64})\s*$")
VERDICT_RE = re.compile(
    r"^Verdict:\s*(CLEAR|BLOCKED（(?:必须修 [1-9]\d* 项(?:，建议修 [1-9]\d* 项)?|建议修 [1-9]\d* 项)）)$")
REPORT_TITLE_RE = re.compile(r"^##\s*第\s*(\d+)\s*轮审核报告")


class StateError(Exception):
    pass


# ---------- 纯函数（供测试） ----------

def parse_scope(text):
    paths = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        p = PurePosixPath(line.replace("\\", "/"))
        if p.is_absolute() or ".." in p.parts:
            raise StateError(f"清单路径必须是根目录内的相对路径：{line}")
        paths.append(str(p))
    if not paths:
        raise StateError("被审文件清单为空")
    return sorted(set(paths))


def fingerprint(file_hashes):
    """file_hashes: {相对路径: sha256 或 'MISSING'}。"""
    text = "".join(f"{p}\t{file_hashes[p]}\n" for p in sorted(file_hashes))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_reviews(text):
    """切出「## 第 k 轮审核报告」小节，返回 (结论列表, 格式不符列表)。"""
    reviews, malformed = [], []
    sections, cur = [], None
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.startswith("## "):
            cur = {"title": line.strip(), "lines": []}
            sections.append(cur)
        elif cur is not None:
            cur["lines"].append(line)
    for s in sections:
        m = REPORT_TITLE_RE.match(s["title"])
        if not m:
            continue
        lines = [l.strip() for l in s["lines"] if l.strip()]
        mb = BASELINE_RE.match(lines[-2]) if len(lines) >= 2 else None
        mv = VERDICT_RE.match(lines[-1]) if lines else None
        if mb and mv:
            reviews.append({"round": int(m.group(1)), "title": s["title"],
                            "baseline": mb.group(1).lower(), "verdict": mv.group(1)})
        else:
            clear_like = any(l.lower().startswith("verdict") and "clear" in l.lower() for l in lines[-3:])
            malformed.append({"round": int(m.group(1)), "title": s["title"], "clear_like": clear_like})
    return reviews, malformed


def assess(current_fp, missing, reviews, malformed, has_snapshot):
    blockers, notes = [], []
    latest = reviews[-1] if reviews else None
    if missing:
        notes.append(f"清单内文件不存在（按 MISSING 计入指纹）：{', '.join(missing)}")
    for m in malformed:
        if latest is None or m["round"] >= latest["round"]:
            if m["clear_like"]:
                blockers.append(f"{m['title']}：疑似 CLEAR 但末两行格式不符，须由审核者追加合规报告")
            else:
                notes.append(f"{m['title']}：末两行格式不符的疑似 BLOCKED，按 BLOCKED 处理，下一轮合规报告取代它")
    if not latest:
        blockers.append("REVIEW.md 中没有任何合规的审核结论")
    else:
        if latest["verdict"] != "CLEAR":
            blockers.append(f"最新结论（第 {latest['round']} 轮）为 {latest['verdict']}")
        if latest["baseline"] != current_fp:
            blockers.append(f"最新结论绑定基线 {latest['baseline'][:12]}，当前为 {current_fp[:12]}：被审文件或清单已变化，须复审")
    if not has_snapshot:
        notes.append("当前基线尚无快照：启动审核者前先运行 snapshot，否则下一轮无法出增量 diff")
    notes.append("最新结论是否确由审核子 Agent 写入（核对回信）；必须修/建议修是否全部独立关闭；仅供参考是否逐项留痕")
    return {"latest": latest, "blockers": blockers, "notes": notes}


# ---------- IO ----------

def review_dir(root):
    return root / ".review"


def load_scope(root):
    f = review_dir(root) / "scope.txt"
    if not f.is_file():
        raise StateError(f"缺少被审文件清单：{f}")
    return parse_scope(f.read_text(encoding="utf-8"))


def hash_files(root, paths):
    out, missing = {}, []
    for p in paths:
        f = root / p
        if f.is_file():
            out[p] = hashlib.sha256(f.read_bytes()).hexdigest()
        else:
            out[p] = "MISSING"
            missing.append(p)
    return out, missing


def snapshot(root):
    paths = load_scope(root)
    hashes, missing = hash_files(root, paths)
    fp = fingerprint(hashes)
    dest = review_dir(root) / "snapshots" / fp
    if not dest.exists():
        tmp = dest.with_name(fp + ".tmp")
        shutil.rmtree(tmp, ignore_errors=True)
        for p in paths:
            if hashes[p] != "MISSING":
                (tmp / "files" / p).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(root / p, tmp / "files" / p)
        tmp.mkdir(parents=True, exist_ok=True)
        (tmp / "manifest.tsv").write_text("".join(f"{p}\t{hashes[p]}\n" for p in paths), encoding="utf-8")
        tmp.rename(dest)
    print(f"基线指纹：{fp}")
    for p in paths:
        print(f"  {hashes[p]}  {p}")
    if missing:
        print(f"缺失文件：{', '.join(missing)}")
    print(f"快照：{dest}")
    return 0


def read_review_md(root):
    f = review_dir(root) / "REVIEW.md"
    return f.read_text(encoding="utf-8") if f.is_file() else ""


def status(root, strict):
    paths = load_scope(root)
    hashes, missing = hash_files(root, paths)
    fp = fingerprint(hashes)
    reviews, malformed = parse_reviews(read_review_md(root))
    out = assess(fp, missing, reviews, malformed, (review_dir(root) / "snapshots" / fp).is_dir())
    print(f"当前基线指纹：{fp}（{len(paths)} 个文件）")
    print(f"审核结论：{len(reviews)} 条")
    for r in reviews:
        mark = "← 当前基线" if r["baseline"] == fp else ""
        print(f"  第 {r['round']} 轮 {r['verdict']} @ {r['baseline'][:12]} {mark}")
    print("阻塞项：" + ("无" if not out["blockers"] else ""))
    for x in out["blockers"]:
        print(f"  - {x}")
    print("需人工核对 / 提示：")
    for x in out["notes"]:
        print(f"  - {x}")
    return 1 if strict and out["blockers"] else 0


def _read_text(f):
    data = f.read_bytes()
    if b"\0" in data[:8192]:
        return None
    return data.decode("utf-8", errors="replace").splitlines(keepends=True)


def diff(root, from_fp):
    if not from_fp:
        reviews, _ = parse_reviews(read_review_md(root))
        if not reviews:
            raise StateError("REVIEW.md 中没有合规的审核结论，无法确定起点；用 --from 指定指纹")
        from_fp = reviews[-1]["baseline"]
    matches = [d for d in (review_dir(root) / "snapshots").glob(from_fp + "*") if d.is_dir() and len(d.name) == 64]
    if len(matches) != 1:
        raise StateError(f"找不到唯一的基线快照 {from_fp[:12]}（.review/snapshots/），无法出增量 diff，需审完整清单")
    snap = matches[0]
    old = dict(l.split("\t", 1) for l in (snap / "manifest.tsv").read_text(encoding="utf-8").splitlines() if l)
    paths = load_scope(root)
    new, _ = hash_files(root, paths)
    changed = 0
    print(f"增量：{snap.name[:12]} → 当前")
    for p in sorted(set(old) | set(new)):
        o, n = old.get(p, "NOT_IN_SCOPE"), new.get(p, "NOT_IN_SCOPE")
        if o == n:
            continue
        changed += 1
        a = _read_text(snap / "files" / p) if o not in ("MISSING", "NOT_IN_SCOPE") else []
        b = _read_text(root / p) if n not in ("MISSING", "NOT_IN_SCOPE") else []
        if a is None or b is None:
            print(f"二进制文件已变化：{p}（{o[:12]} → {n[:12]}）")
            continue
        sys.stdout.writelines(difflib.unified_diff(a, b, f"a/{p}", f"b/{p}"))
        print()
    print(f"共 {changed} 个文件变化")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("snapshot", "status", "diff"))
    ap.add_argument("--root", default=".", help="工作区根目录（含 .review/）")
    ap.add_argument("--strict", action="store_true", help="status：有阻塞项时退出码 1")
    ap.add_argument("--from", dest="from_fp", help="diff：起点指纹（可写前缀）")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    if a.command == "snapshot":
        return snapshot(root)
    if a.command == "status":
        return status(root, a.strict)
    return diff(root, a.from_fp)


if __name__ == "__main__":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        sys.exit(main())
    except StateError as e:
        print(e, file=sys.stderr)
        sys.exit(2)
