# MySkills

个人 Claude Code skill 集合。本仓库每个顶层目录都是一个可独立安装的 skill（含 `SKILL.md`），其他 agent（Claude Code CLI、Claude Desktop，或任何读取 `~/.claude/skills/` 的宿主）都可以直接拉取本仓库安装。

## Skill 列表

| Skill | 用途 | 搭配 / 依赖 |
|---|---|---|
| [start-context](./start-context/) | 接手开发上下文：新 agent 开始工作、接手旧窗口时，读取 `docs/agent-context/` 交接入口并核实当前可执行状态 | 与 [end-context](./end-context/) 成对（读侧），建议一起安装 |
| [end-context](./end-context/) | 保存开发交接：结束工作、切换窗口前增量维护项目架构、改动、待办与命令经验 | 与 [start-context](./start-context/) 成对（写侧），建议一起安装 |
| [deep-research](./deep-research/) | 结构化深度研究三阶段流水线（outline → 并行 deep → report） | Exa MCP 可选（有 DuckDuckGo 兜底）；使用子 agent（Agent 工具） |
| [pr-review-loop](./pr-review-loop/) | PR 审核闭环：修改方/审核方分离，循环审核至 `Verdict: CLEAR` 且 CI 全绿才合并 | `gh` CLI + git + CI；使用子 agent（Agent 工具） |

## 安装

前置条件：已安装 `git`；目标环境使用用户级 skill 目录 `~/.claude/skills/`（Claude Code 的默认位置）。

### 1. 克隆仓库

```bash
git clone --depth 1 https://github.com/1010323691/MySkills.git
```

### 2. 复制目标 skill 目录

目录名必须保持不变（需与 `SKILL.md` frontmatter 的 `name` 一致）：

Linux / macOS / Windows Git Bash：

```bash
cp -r MySkills/<skill名> ~/.claude/skills/
```

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse "MySkills\<skill名>" "$HOME\.claude\skills\"
```

本仓库可用的 `<skill名>`：`start-context`、`end-context`、`deep-research`、`pr-review-loop`。

### 3. 验证

```bash
test -f ~/.claude/skills/<skill名>/SKILL.md && echo OK
```

然后重启 Claude Code（或开新会话），skill 列表中出现对应条目即安装成功。

### 更新

```bash
cd MySkills && git pull
cp -r MySkills/<skill名> ~/.claude/skills/   # 重新复制覆盖
```

### 卸载

```bash
rm -rf ~/.claude/skills/<skill名>
# Windows PowerShell: Remove-Item -Recurse "$HOME\.claude\skills\<skill名>"
```

## 说明

- `start-context` / `end-context` 实现 `context-protocol/v2` 交接协议：交接文档存放在**目标项目**的 `docs/agent-context/`，由 end-context 写入、start-context 读取；两个 skill 只管理该目录内的 Markdown 文档，不修改业务代码。
- 本仓库均为纯提示词型 skill（`SKILL.md` + 可选的 references/scripts/templates），无二进制依赖；`start-context`/`end-context` 中的 `scripts/context_check.py` 为可选的只读结构检查脚本（Python 3.9+）。
- 每个 skill 目录下另有独立 README（功能、用法、目录结构、注意事项）。
