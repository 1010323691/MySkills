# MySkills

个人 Agent skill 集合。每个顶层目录是一个可独立安装的 skill（`SKILL.md` 标准：目录 + `SKILL.md` + 可选 references/scripts/assets），纯提示词内容，无二进制依赖。各目录内的 `README.md` 介绍该 skill 的用途与使用方法。

| Skill | 用途 |
|---|---|
| [start-context](./start-context/) | 接手开发上下文（读侧）：新 agent 开始工作、接手旧窗口时读取交接入口并核实可执行状态 |
| [end-context](./end-context/) | 保存开发交接（写侧）：结束工作、切换窗口前增量维护项目上下文文档 |
| [deep-research](./deep-research/) | 结构化深度研究：outline → 并行 deep → report 三阶段流水线 |
| [pr-review-loop](./pr-review-loop/) | PR 审核闭环：修改方/审核方分离，循环至 `Verdict: CLEAR` 且 CI 全绿才合并 |
| [local-review-loop](./local-review-loop/) | 本地审核闭环（无 PR 介质）：修改方/审核方分离，不建 PR/CI，用文件哈希基线锚定结论，循环至 `Verdict: CLEAR` 收尾 |
| [convert-chm-to-txt](./convert_chm_to_txt/) | CHM 转常规 txt：自动识别阅读器式/HTML Help/纯文本三种结构，输出 UTF-8（BOM）纯文本、分章与目录 |
| [book-to-skill](./book-to-skill/) | 书/文档 → Agent skill 转换器：提取框架/心智模型/反模式生成完整 skill（含本地 Step 6.5 原文自动备份规则） |

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
- `pr-review-loop` 依赖 `gh` CLI（已登录、具备 repo scope）与可用的 CI。
- `local-review-loop` 依赖宿主支持启动子 agent（Agent 工具），无其他外部依赖；适用于非 git 目录，或在 git 仓库中不想/不便开 PR 的改动。
- `convert-chm-to-txt` 依赖 7-Zip（解包 CHM，`winget install 7zip.7zip -e --silent --disable-interactivity` 可装）与 Python 3；转换脚本 `scripts/convert_chm_to_txt.py`。
- `book-to-skill` 基于开源项目 [virgiliojr94/book-to-skill](https://github.com/virgiliojr94/book-to-skill)（MIT，含本地 Step 6.5 修改）；依赖 Python 3（可选 Calibre 与 `gh`），`SKILL.md` + `scripts/` + `tools/` + `book_to_skill/` 须整体成目录复制安装。
