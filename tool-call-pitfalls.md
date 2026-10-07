# 工具调用陷阱（Tool Call Pitfalls）

记录当前运行环境中**无法被 Agent 识别、无法执行的工具**。凡是发出过调用却不存在于可用工具列表的工具，一律禁止再次调用，必须使用对应替代方案。

**规则**

1. 每当一次工具调用因「工具不存在 / 无法识别 / 无法执行」而失败时，立即在本文件追加一条记录。
2. 不确定某工具在当前环境是否存在时，先核对会话提供的可用工具列表，再决定是否调用；拿不准就降级到 Bash 替代。
3. 本文件与个人记忆 `~/.claude/projects/D--projectPath-MySkills/memory/tool-call-pitfalls.md` 保持同步：新增陷阱时两边同时更新。

**条目格式**

```
## <工具名>
- 首次记录：YYYY-MM-DD ｜ 环境
- 现象：
- 原因：
- 替代方案：
```

---

## TodoWrite

- 首次记录：2026-10-07 ｜ Claude 桌面应用（Code tab），Windows / Git Bash
- 现象：模型发出 `TodoWrite` 调用，Agent 无法识别该工具、无法执行（本环境可用工具列表中不含任务清单工具）。
- 原因：当前 harness 的工具集里没有 TodoWrite。
- 替代方案：用回复正文中的文本清单跟踪任务进度，或在本地维护一个任务清单文件。**禁止再调用 TodoWrite。**

## Grep

- 首次记录：2026-10-07 ｜ Claude 桌面应用（Code tab），Windows / Git Bash
- 现象：模型发出 `Grep` 调用，Agent 无法识别该工具、无法执行（本环境可用工具列表中不含 Grep）。
- 原因：当前 harness 的工具集里没有 Grep（只有 Glob 按文件名匹配）。
- 替代方案：文件名匹配用 `Glob`；内容搜索用 Bash 执行 `grep -rn "<pattern>" <path>`（Git Bash 自带 grep）。**禁止再调用 Grep。**
