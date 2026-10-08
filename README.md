# MySkills

个人 Agent skill 集合。每个顶层目录是一个可独立安装的 skill（`SKILL.md` 标准：目录 + `SKILL.md` + 可选 references/scripts/assets），部分 skill 附带脚本；各目录内的 `README.md` 介绍该 skill 的用途、来源与依赖。

| Skill | 用途 |
|---|---|
| [start-context](./start-context/) | 接手开发上下文（读侧）：新 agent 开始工作、接手旧窗口时读取交接入口并核实可执行状态 |
| [end-context](./end-context/) | 保存开发交接（写侧）：结束工作、切换窗口前增量维护项目上下文文档 |
| [deep-research](./deep-research/) | 结构化深度研究：outline → 并行 deep → report 三阶段流水线 |
| [pr-review-loop](./pr-review-loop/) | PR 审核闭环：修改方/审核方分离，循环至 `Verdict: CLEAR` 且 CI 全绿才合并 |
| [local-review-loop](./local-review-loop/) | 本地审核闭环（无 PR 介质）：修改方/审核方分离，不建 PR/CI，用文件哈希基线锚定结论，循环至 `Verdict: CLEAR` 收尾 |
| [convert-chm-to-txt](./convert-chm-to-txt/) | CHM 转常规 txt：自动识别阅读器式/HTML Help/纯文本三种结构，输出 UTF-8（BOM）纯文本、分章与目录 |
| [book-to-skill](./book-to-skill/) | 书/文档 → Agent skill 转换器：提取框架/心智模型/反模式生成完整 skill（含本地 Step 6.5 原文自动备份规则） |
| [torrentclaw](./torrentclaw/) | TorrentClaw 影视 torrent 检索：聚合 30+ 来源，按画质/语言/HDR/季集筛选，磁力直投 Transmission/aria2 |
| [lov-media-fetch](./lov-media-fetch/) | 影视寻宝端到端闭环：多源发现 → 排序选版 → 容量预检 → aria2 测速下载 → ffprobe 验收出报告 |
| [the-pirate-bay](./the-pirate-bay/) | The Pirate Bay 检索与磁力提取：apibay.org JSON API，整季/电影智能搜索，按 seeders 与可信上传者排序 |
| [JavBus-GetMagnet](./JavBus-GetMagnet/) | JavBus 磁力 + 封面：自动过 18+ 验证门，每作选最小 1080p（无则 720p），生成自包含展示页（含「获取更新」） |
| [movie-magnet-hunt](./movie-magnet-hunt/) | 片单批量磁力检索：sidhub/番号楼/6V 三源，默认「1080p 中文字幕优先」，消歧同名片、验证磁力，输出 资源清单.md + magnets.txt |
| [skill-creator](./skill-creator/) | 创建/迭代 skill 官方版：草稿 → 跑 evals → 定性+定量评审 → 重写循环，含 description 触发优化脚本 |
| [tool-call-pitfalls](./tool-call-pitfalls/) | 工具调用陷阱记录与同步：仓库 tool-call-pitfalls.md 为事实源，同步 CLAUDE.md 与个人记忆，含新增/移除（按环境补充观察）/核对三模式与 dry run |

## 安装方式

通用做法：克隆本仓库，把目标 skill 目录**原样复制**到宿主对应的 skills 目录。目录名不能改（需与 `SKILL.md` frontmatter 的 `name` 一致）：

```bash
git clone --depth 1 https://github.com/1010323691/MySkills.git
```

### Claude（Claude Code CLI / 桌面版）

用户级 skills 目录：`~/.claude/skills/`

Linux / macOS / Git Bash：

```bash
mkdir -p ~/.claude/skills
cp -r MySkills/start-context ~/.claude/skills/
cp -r MySkills/end-context ~/.claude/skills/
# 按需：deep-research、pr-review-loop
```

Windows PowerShell：

```powershell
Copy-Item -Recurse -Force "MySkills\start-context" "$HOME\.claude\skills\"
```

重启 Claude Code（或开新会话）后生效。验证：`test -f ~/.claude/skills/start-context/SKILL.md && echo OK`。

### Codex（Codex CLI）

个人级 skills 目录：`~/.agents/skills/`（对本机所有仓库生效）；也可放进目标仓库的 `.agents/skills/`（仓库级，仅该仓库生效）。

Linux / macOS / Git Bash：

```bash
mkdir -p ~/.agents/skills
cp -r MySkills/start-context ~/.agents/skills/
cp -r MySkills/end-context ~/.agents/skills/
```

Windows PowerShell：

```powershell
Copy-Item -Recurse -Force "MySkills\start-context" "$HOME\.agents\skills\"
```

Codex 会自动检测新增的 skill；没有立即出现时重启 Codex。也可以在 Codex 会话里让内置的 skill-installer 直接从本仓库安装，例如：「用 skill-installer 从 https://github.com/1010323691/MySkills 安装 start-context」。

只想临时停用（不删除）时，在 `~/.codex/config.toml` 中添加：

```toml
[[skills.config]]
path = "/path/to/skill/SKILL.md"
enabled = false
```

### 更新与卸载

更新：拉取后重新复制覆盖；卸载：删除对应的 skill 目录。

Linux / macOS / Git Bash：

```bash
cd MySkills && git pull
cp -r <skill名> ~/.claude/skills/    # 源为克隆内相对路径；Codex 换成 ~/.agents/skills/
rm -rf ~/.claude/skills/<skill名>
```

Windows PowerShell：

```powershell
cd MySkills; git pull
Copy-Item -Recurse -Force "<skill名>" "$HOME\.claude\skills\"    # -Force：更新场景目标已存在需覆盖；Codex 换成 "$HOME\.agents\skills\"
Remove-Item -Recurse "$HOME\.claude\skills\<skill名>"
```

## 备注

- `start-context` / `end-context` 实现 `context-protocol/v2` 交接协议，交接文档存放在目标项目的 `docs/agent-context/`，建议成对安装；`scripts/context_check.py` 为可选的只读结构检查脚本（Python 3.9+）。
- `deep-research` 依赖 Exa MCP（可选，未安装时走 DuckDuckGo 兜底通道）与子 agent 工具。
- `pr-review-loop` 依赖已登录且具备所需仓库权限的 `gh` CLI 与独立子 agent；适用 CI 必须通过，核实确无适用 CI 时记录不适用。
- `local-review-loop` 依赖宿主支持启动子 agent（Agent 工具），无其他外部依赖；适用于非 git 目录，或在 git 仓库中不想/不便开 PR 的改动。
- `convert-chm-to-txt` 依赖 7-Zip（解包 CHM，`winget install 7zip.7zip -e --silent --disable-interactivity` 可装）与 Python 3；转换脚本 `scripts/convert_chm_to_txt.py`。
- `book-to-skill` 基于开源项目 [virgiliojr94/book-to-skill](https://github.com/virgiliojr94/book-to-skill)（MIT，含本地 Step 6.5 修改）；依赖 Python 3（可选 Calibre 与 `gh`），`SKILL.md` + `scripts/` + `tools/` + `book_to_skill/` 须整体成目录复制安装。
- `torrentclaw` 为上游 [torrentclaw/torrentclaw-skill](https://github.com/torrentclaw/torrentclaw-skill)（MIT）完整副本；依赖 bash + curl，下载需本机 Transmission 或 aria2，API 匿名可用（可选 `TORRENTCLAW_API_KEY` 提额）。
- `lov-media-fetch` 为上游 [lovstudio/media-fetch-skill](https://github.com/lovstudio/media-fetch-skill)（MIT）完整副本（不含上游测试案例 `cases/`）；依赖 Python 3.9+ 与 aria2 1.36+，验收需 ffprobe，qBittorrent 可选。
- `the-pirate-bay` 取自 [glittercowboy/taches-cc-resources](https://github.com/glittercowboy/taches-cc-resources)（MIT）原样副本；依赖 Node.js（`npx tsx` 按需拉取运行时）。
- `JavBus-GetMagnet` 为自制；依赖 Python 3（仅标准库）与 javbus.com 网络；`cookies.txt`（年龄验证 + 会话缓存）为本地文件，不入仓库（被目录内 `.gitignore` 忽略），首次运行自动产生，验证门重现时删除重跑即可。
- `movie-magnet-hunt` 为自制（2026-10-07 实战固化）；依赖真 Python 3（Windows 上 `python3` 可能是静默失败的 stub）与 sidhub/番号楼/6V 三站连通；`evals/` 含评测案例。
- `skill-creator` 为 Anthropic 官方 skill 完整副本（Apache-2.0，见其 `LICENSE.txt`），未做修改；依赖 Python 3，跑 evals 需宿主能启动子 agent。
- `tool-call-pitfalls` 为自制（2026-10-07 实战固化）；无外部依赖（git + 文件读写）；路径绑定本机（`D:\projectPath\MySkills` 与个人记忆目录），换机器安装前需改 `SKILL.md` 路径表；`evals/` 含评测案例。
