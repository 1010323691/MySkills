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
- 替代方案：文件名匹配用 `Glob`；内容搜索用 Bash 执行 `grep -rn "<pattern>" <path>`（Git Bash 自带 grep）。**调用前先核对当前会话函数表是否有 Grep，没有则禁止调用。**
- 补充：2026-10-07 在 Claude 桌面应用（Code tab）当前会话观察到可用（Grep 在函数表中，实测调用成功）；禁令仅适用于函数表不含 Grep 的环境。

## gh pr merge（Claude 桌面应用 auto 模式）

- 首次记录：2026-10-12 ｜ Claude 桌面应用（Code tab）auto 模式，Windows 11 / Git Bash，单账号仓库（owner = PR 作者）
- 现象：`gh pr merge <N> --repo <R> --match-head-commit <SHA> --merge` 被自动模式分类器拒绝，原因 `[Merge Without Review]`（PR 无 GitHub 正式 review approval 记录时触发）。补正式 approval 的路径也不通：`gh pr review --approve` 被 GitHub 拒绝（作者不能 approve 自己的 PR，"Can not approve your own pull request"），单账号仓库拿不到第二账号的正式 approval。
- 原因：自动模式分类器把「无正式 review 的 PR 合并」判为高风险；pr-review-loop 的独立审核记录（独立子 Agent、PR 评论、Reviewed-Head/Verdict 行）不写入 GitHub 正式 review 状态，单账号仓库 reviewDecision 恒为空。
- 替代方案：**不重试同一命令、不用直推 main 等变通**。pr-review-loop 门禁全满足时把带 `--match-head-commit <已审核 SHA>` 的精确合并命令交接给用户手动执行，或请用户在 default 模式放行该命令 / 为 Bash 添加权限规则；合并落地后 agent 在本会话继续确认 MERGED 与安全清理分支。
