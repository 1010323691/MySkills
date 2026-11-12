# codex-image-gen — 用本机 Codex 调 GPT 生图

## 用途

让 Claude Code 这类不能直接生成位图的 agent，借本机 Codex CLI（登录 ChatGPT 账号）调用 GPT 图像模型，产出真正的 PNG 图片：

- **单张**：一段提示词 → 一张图，可指定尺寸、质量、参考图；
- **一组图风格一致**：先定稿一张「风格锚点」，其余每张都带它作参考图；
- **并发批量**：提示词目录里每个 `名字.txt` → `名字.png`，同时生成多张，失败的重跑同一条命令即可补齐；
- **总览图**：把一批图拼成一张带文件名的总览，方便一次确认。

## 使用方法

对 agent 说即可（触发 [SKILL.md](SKILL.md)），例如：

- 「用 GPT 生一张这个页面的效果图」
- 「这 20 段提示词并发批量出图，风格按第一张」
- 「画一张 1024×1024 的应用图标」

也可以直接跑脚本：

```bash
# 单张
scripts/codex_image.sh -o out/hero.png -p prompts/hero.txt -s 1536x1024
scripts/codex_image.sh -o out/icon.png -t "一个扁平风格的耳机图标，白底" -s 1024x1024

# 批量：prompts/*.txt → out/*.png，同时 3 张，统一带参考图
scripts/codex_batch.sh -d prompts -o out -j 3 -r out/anchor.png

# 只演示（打印找到的 codex、命令和提示词开头，不真的生成）
scripts/codex_image.sh -n -o /tmp/x.png -t 测试

# 总览图（需要 Pillow）
python3 scripts/contact_sheet.py out/_总览.png out/*.png
```

提示词文件开头可写指令行给个别图片单独指定：`@size: 1024x1536`、`@quality: medium`、`@ref: 另一张.png`（替换 `-r` 给的参考图，可写多行）、`@ref: none`（不用参考图）。

## 依赖

- Codex CLI，登录 ChatGPT 账号，且 `codex features list` 里 `image_generation` 为 true。macOS 上装了 ChatGPT 桌面版就自带（`/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex`，PATH 里通常没有），否则 `npm i -g @openai/codex`。其他位置用环境变量 `CODEX_BIN` 指定。
- bash（兼容 macOS 自带的 3.2）、`xargs`、`mktemp`；失败诊断用到 `python3`。
- 总览图需要 Pillow（`python3 -m pip install pillow`）。
- 每张图消耗 ChatGPT 账号的额度。

## 来源

自制。2026-11-11 在一个 Web 应用的 UI 重设计中实战固化：用这套做法生成了 21 张高保真页面效果图（先定稿 1 张风格锚点，其余带参考图并发生成，最多 8 张同时跑，每张 1～3 分钟，全部一次成功）；codex-cli 0.167。
