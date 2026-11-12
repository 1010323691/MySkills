#!/bin/bash
# 用本机 Codex CLI（ChatGPT 账号）调用 GPT 生图：生成恰好 1 张图片，复制到 -o 指定的位置。
#
# 用法：
#   codex_image.sh -o OUT.png (-p PROMPT_FILE | -t "提示词") [-r REF.png]... [-s 1536x1024] [-q high] [-l LOG_DIR] [-n]
#
#   -o  输出图片路径（必填；扩展名按 Codex 实际产出的格式，一般是 .png）
#   -p  提示词文件（UTF-8 文本）；与 -t 二选一
#   -t  直接给提示词文本
#   -r  参考图，可重复（保持系列风格一致时传「定稿的那张」）
#   -s  尺寸，默认 1536x1024（横版）；竖版 1024x1536，方图 1024x1024；也可写「1792x1024 或最接近的超宽横版」
#   -q  质量，默认 high
#   -l  日志目录，默认「输出目录/.codex-image-logs」（每张图留 .in 提示词、.jsonl 事件流、.err 标准错误）
#   -n  只演示：打印将要执行的命令和提示词开头，不真的调用
#
# 提示词文件开头可写指令行（会从提示词里去掉，优先于命令行参数，批量时给个别图片单独指定）：
#   @size: 1024x1536      @quality: medium      @ref: none（不用参考图）
#   @ref: style.png（相对提示词文件所在目录；写了 @ref 就替换命令行 -r 给的参考图，可写多行）
#
# 结果：成功输出「OK 名字 -> 路径 (耗时)」，退出码 0；失败输出「FAIL 名字 …」和模型最后一句回复 / 错误尾部，退出码 1。
# 环境变量：CODEX_BIN 指定 codex 可执行文件；CODEX_HOME 改 Codex 数据目录（默认 ~/.codex，图片落在其 generated_images/ 下）。
set -u

usage() { sed -n '2,/^set -u$/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'; exit 2; }

out="" prompt_file="" prompt_text="" size="1536x1024" quality="high" log_dir="" dry=0
refs=()
while getopts "o:p:t:r:s:q:l:nh" opt; do
  case "$opt" in
    o) out="$OPTARG" ;;
    p) prompt_file="$OPTARG" ;;
    t) prompt_text="$OPTARG" ;;
    r) refs+=("$OPTARG") ;;
    s) size="$OPTARG" ;;
    q) quality="$OPTARG" ;;
    l) log_dir="$OPTARG" ;;
    n) dry=1 ;;
    *) usage ;;
  esac
done
[ -n "$out" ] || usage
if [ -n "$prompt_file" ] && [ -n "$prompt_text" ]; then echo "只能用 -p 或 -t 其中一个" >&2; exit 2; fi
if [ -z "$prompt_file" ] && [ -z "$prompt_text" ]; then echo "缺少提示词：用 -p 文件 或 -t 文本" >&2; exit 2; fi
if [ -n "$prompt_file" ] && [ ! -f "$prompt_file" ]; then echo "找不到提示词文件：$prompt_file" >&2; exit 2; fi

name="$(basename "$out")"; name="${name%.*}"

# ---- 找 codex：CODEX_BIN → PATH → ChatGPT 桌面版自带的 Codex CLI（macOS 上 PATH 里通常没有 codex）----
find_codex() {
  if [ -n "${CODEX_BIN:-}" ]; then
    [ -x "$CODEX_BIN" ] && { echo "$CODEX_BIN"; return 0; }
    echo "CODEX_BIN 不可执行：$CODEX_BIN" >&2; return 1
  fi
  if command -v codex >/dev/null 2>&1; then command -v codex; return 0; fi
  local candidate
  for candidate in \
    "/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex" \
    "$HOME/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex"; do
    [ -x "$candidate" ] && { echo "$candidate"; return 0; }
  done
  return 1
}
codex="$(find_codex)" || {
  echo "FAIL $name 找不到 codex：装 ChatGPT 桌面版（自带 Codex CLI）或 npm i -g @openai/codex，再 codex login；也可以用 CODEX_BIN 指定路径" >&2
  exit 1
}

# ---- 提示词：读出正文，并取出开头的 @size / @quality / @ref 指令行 ----
if [ -n "$prompt_file" ]; then
  prompt_dir="$(cd "$(dirname "$prompt_file")" && pwd)"
  body=""
  in_header=1
  file_refs=0   # 提示词文件里第一次出现 @ref 时，先清掉命令行给的参考图
  while IFS= read -r line || [ -n "$line" ]; do
    if [ "$in_header" = 1 ]; then
      case "$line" in
        @size:*) size="$(echo "${line#@size:}" | sed 's/^ *//; s/ *$//')"; continue ;;
        @quality:*) quality="$(echo "${line#@quality:}" | sed 's/^ *//; s/ *$//')"; continue ;;
        @ref:*)
          ref="$(echo "${line#@ref:}" | sed 's/^ *//; s/ *$//')"
          [ "$file_refs" = 0 ] && refs=()
          file_refs=1
          if [ "$ref" != "none" ]; then case "$ref" in /*) ;; *) ref="$prompt_dir/$ref" ;; esac; refs+=("$ref"); fi
          continue ;;
        "") continue ;;
        *) in_header=0 ;;
      esac
    fi
    body="$body$line"$'\n'
  done < "$prompt_file"
else
  body="$prompt_text"
fi
unique=()
for ref in ${refs[@]+"${refs[@]}"}; do
  [ -f "$ref" ] || { echo "FAIL $name 找不到参考图：$ref" >&2; exit 1; }
  # 转成绝对路径：codex 用 -C 在临时目录里工作，相对路径可能按那个目录解析
  ref="$(cd "$(dirname "$ref")" && pwd)/$(basename "$ref")"
  seen=0
  for kept in ${unique[@]+"${unique[@]}"}; do [ "$kept" = "$ref" ] && seen=1; done
  [ "$seen" = 0 ] && unique+=("$ref")
done
refs=(${unique[@]+"${unique[@]}"})

# 固定开场白：codex 是编程 agent，不说清楚它会先写代码、跑命令或反问，而不是直接调用生图工具。
preamble="请直接调用你的图像生成工具生成恰好 1 张图片：尺寸 ${size}，质量 ${quality}。不要写代码、不要运行任何命令、不要修改任何文件，也不要先确认或提问。生成完成后只回复「完成」。"
if [ ${#refs[@]} -gt 0 ]; then
  preamble="$preamble
附带的图片是参考图：按下面需求里的说法使用它；需求没有说明时，沿用它的整体风格、配色、字体与排版语言，但不要照搬它的具体内容。"
fi

out_dir="$(cd "$(dirname "$out")" 2>/dev/null && pwd)" || { mkdir -p "$(dirname "$out")" && out_dir="$(cd "$(dirname "$out")" && pwd)"; }
out="$out_dir/$(basename "$out")"
log_dir="${log_dir:-$out_dir/.codex-image-logs}"
mkdir -p "$log_dir"
input="$log_dir/$name.in"
{ printf '%s\n以下是图片需求：\n\n' "$preamble"; printf '%s\n' "$body"; } > "$input"

# 在空的临时目录里以只读沙箱运行：codex 碰不到你的项目文件；不在 git 仓库里时需要 --skip-git-repo-check。
# 注意 -i 会贪婪地吃掉后面的参数，所以参考图放在 --json 之前，最后的「-」（从标准输入读提示词）前面必须隔着别的选项。
tmp_base="${TMPDIR:-/tmp}"; tmp_base="${tmp_base%/}"
work="$(mktemp -d "$tmp_base/codex-image.XXXXXX")"
args=(exec --skip-git-repo-check -s read-only -C "$work")
for ref in ${refs[@]+"${refs[@]}"}; do args+=(-i "$ref"); done
args+=(--json -)

if [ "$dry" = 1 ]; then
  echo "codex: $codex"
  printf 'args:'; printf ' %q' "${args[@]}"; echo
  echo "输出：$out"; echo "日志：$log_dir/$name.{in,jsonl,err}"
  echo "----- 提示词（前 12 行）-----"; head -12 "$input"
  rmdir "$work" 2>/dev/null
  exit 0
fi

codex_home="${CODEX_HOME:-$HOME/.codex}"
started=$(date +%s)
"$codex" "${args[@]}" < "$input" > "$log_dir/$name.jsonl" 2> "$log_dir/$name.err"
status=$?
rmdir "$work" 2>/dev/null
elapsed=$(( $(date +%s) - started ))

# 事件流里没有图片路径：图片落在 $CODEX_HOME/generated_images/<thread_id>/ 下，按 thread_id 去找。
tid="$(grep -o '"thread_id":"[^"]*"' "$log_dir/$name.jsonl" 2>/dev/null | head -1 | cut -d'"' -f4)"
img=""
if [ -n "$tid" ] && [ -d "$codex_home/generated_images/$tid" ]; then
  img="$(ls -t "$codex_home/generated_images/$tid"/*.png "$codex_home/generated_images/$tid"/*.jpg \
             "$codex_home/generated_images/$tid"/*.jpeg "$codex_home/generated_images/$tid"/*.webp 2>/dev/null | head -1)"
fi

if [ -n "$img" ]; then
  cp "$img" "$out"
  echo "OK $name -> $out (${elapsed}s)"
  exit 0
fi

echo "FAIL $name (codex 退出码 $status，thread ${tid:-无}，${elapsed}s)"
last_reply="$(python3 -I - "$log_dir/$name.jsonl" 2>/dev/null <<'PY'
import json, sys
text = ""
for line in open(sys.argv[1], encoding="utf-8", errors="replace"):
    try:
        event = json.loads(line)
    except ValueError:
        continue
    item = event.get("item") or {}
    if item.get("type") == "agent_message" and item.get("text"):
        text = item["text"]
    if event.get("type") in ("error", "turn.failed"):
        text = json.dumps(event, ensure_ascii=False)
print(text.strip()[:600])
PY
)"
[ -n "$last_reply" ] && echo "  模型最后的回复：$last_reply"
tail -n 5 "$log_dir/$name.err" 2>/dev/null | sed 's/^/  /'
exit 1
