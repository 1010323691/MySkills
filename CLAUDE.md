# CLAUDE.md

本仓库（MySkills）是 Claude Skill 集合：每个子目录是一个 skill（含 `SKILL.md`），另有散落的顶层 `.md` 提示词模板（如 `workflow-to-skill-prompt.md`）。提交信息用中文。

## 工具调用陷阱

部分工具**无法被 Agent 识别**，发出调用会失败；可用性按环境（harness/版本）而异，调用前先核对当前会话的可用工具列表。`TodoWrite`：所有已观察环境均不可用，**禁止再调用**；`Grep`：桌面应用旧版本不可用、当前版本可用，**仅在确认当前会话函数表存在时才可调用**。

- 完整清单、现象与替代方案：见 [tool-call-pitfalls.md](tool-call-pitfalls.md)
- 个人记忆（每次会话自动加载）：`~/.claude/projects/D--projectPath-MySkills/memory/tool-call-pitfalls.md`
- 遇到新的不可用工具：两边同步追加条目。
