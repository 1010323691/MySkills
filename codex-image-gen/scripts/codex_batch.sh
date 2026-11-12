#!/bin/bash
# 并发批量生图：提示词目录里每个 NAME.txt → 输出目录/NAME.png，同时跑 -j 个（每个都是独立的 codex 会话）。
#
# 用法：
#   codex_batch.sh -d PROMPTS_DIR -o OUT_DIR [-j 3] [-r REF.png]... [-s 1536x1024] [-q high] [-f] [-n]
#
#   -d  提示词目录（只取 *.txt；文件名去掉 .txt 就是图片名）
#   -o  输出目录
#   -j  同时生成几张，默认 3（实测最多 8 张同时也都成功；每张 1～3 分钟，偶尔 6～7 分钟）
#   -r  所有图片共用的参考图，可重复；个别图片在提示词文件开头写 @ref: 换成别的（可写多行）或 @ref: none 去掉
#   -s  默认尺寸（个别图片用 @size: 覆盖）；-q 默认质量
#   -f  已经有同名图片也重新生成（默认跳过，所以失败后直接重跑本命令就只补失败的）
#   -n  只演示：列出要生成的图片和每张的命令，不真的调用
#
# 每张的结果行（OK / FAIL）同时写进「输出目录/_batch.log」；全部成功退出码 0，有失败退出码 1。
set -u

usage() { sed -n '2,/^set -u$/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'; exit 2; }

here="$(cd "$(dirname "$0")" && pwd)"
dir="" out="" jobs=3 size="1536x1024" quality="high" force=0 dry=0
refs=()
while getopts "d:o:j:r:s:q:fnh" opt; do
  case "$opt" in
    d) dir="$OPTARG" ;;
    o) out="$OPTARG" ;;
    j) jobs="$OPTARG" ;;
    r) refs+=("$OPTARG") ;;
    s) size="$OPTARG" ;;
    q) quality="$OPTARG" ;;
    f) force=1 ;;
    n) dry=1 ;;
    *) usage ;;
  esac
done
[ -n "$dir" ] && [ -n "$out" ] || usage
[ -d "$dir" ] || { echo "找不到提示词目录：$dir" >&2; exit 2; }
case "$jobs" in ''|*[!0-9]*|0) echo "-j 要是正整数" >&2; exit 2 ;; esac
mkdir -p "$out"
dir="$(cd "$dir" && pwd)"; out="$(cd "$out" && pwd)"

names=()
for file in "$dir"/*.txt; do
  [ -f "$file" ] || continue
  name="$(basename "$file" .txt)"
  if [ "$force" = 0 ] && [ -f "$out/$name.png" ]; then
    echo "SKIP $name（已有 $out/$name.png，用 -f 重新生成）"
    continue
  fi
  names+=("$name")
done
if [ ${#names[@]} -eq 0 ]; then echo "没有要生成的图片"; exit 0; fi

common=(-s "$size" -q "$quality" -l "$out/.codex-image-logs")
for ref in ${refs[@]+"${refs[@]}"}; do common+=(-r "$ref"); done
[ "$dry" = 1 ] && common+=(-n)

echo "开始：${#names[@]} 张，同时 $jobs 张 → $out"
log="$out/_batch.log"
tmp_base="${TMPDIR:-/tmp}"; run_log="$(mktemp "${tmp_base%/}/codex-batch.XXXXXX")"
[ "$dry" = 1 ] || echo "===== $(date '+%F %T') 开始 ${#names[@]} 张 =====" >> "$log"
started=$(date +%s)
# 每张一个独立 codex 会话，互不影响。图片名以 NUL 分隔传给 xargs（名字里有空格也安全），由 xargs 追加在命令末尾；
# 不用 xargs -I：macOS 的 -I 替换后每个参数限 255 字节，长路径或中文名会失败。
run_one='name="${@: -1}"; set -- "${@:1:$(($# - 1))}"; script="$1"; dir="$2"; out="$3"; shift 3; exec "$script" -p "$dir/$name.txt" -o "$out/$name.png" "$@"'
printf '%s\0' "${names[@]}" \
  | xargs -0 -n 1 -P "$jobs" bash -c "$run_one" _ "$here/codex_image.sh" "$dir" "$out" "${common[@]}" \
  | tee "$run_log"
if [ "$dry" = 1 ]; then rm -f "$run_log"; exit 0; fi
cat "$run_log" >> "$log"

elapsed=$(( $(date +%s) - started ))
ok=0; failed=()
for name in "${names[@]}"; do
  if grep -qF -- "OK $name -> " "$run_log"; then ok=$((ok + 1)); else failed+=("$name"); fi
done
rm -f "$run_log"
echo "===== 完成：成功 $ok 张，失败 ${#failed[@]} 张，用时 ${elapsed}s =====" | tee -a "$log"
if [ ${#failed[@]} -gt 0 ]; then
  echo "失败：${failed[*]}（日志在 $out/.codex-image-logs/；直接重跑本命令只会补这几张）"
  exit 1
fi
exit 0
