# local-review-loop — 本地审核闭环（无 PR 介质）

> 安装方式见[仓库根 README](../README.md)（Claude 与 Codex 通用）。

## 用途

修改方/审核方分离的**本地**审核全流程，`Verdict: CLEAR` 是唯一通过/收尾入口。与 [pr-review-loop](../pr-review-loop/) 共用同一套审核协议内核，差异只在审核介质——**不建分支、不建 PR、不等 CI、不合并**，适用于「代码不上 git」或「在 git 仓库但不想/不便开 PR」的场景：

1. **主 Agent**：代码修改完成且本地基础验证通过后，显式圈定「被审文件清单」作为审核范围，并对该文件集合计算**内容哈希基线**，写入本地审核记录文件 `.review/REVIEW.md`，启动审核子 Agent
2. **审核子 Agent**：把结构化审核报告（标号发现项 / 三级严重度 / `Verdict` 结论行）追加写入 `.review/REVIEW.md`，**不修改代码**
3. **主 Agent**：对每个发现项（含「建议修」「仅供参考」）逐项审视——合理即落地修复并逐项写入处理报告；不合理才书面反驳，经审核子 Agent 再裁决后跳过
4. 每轮新起复审子 Agent，循环至 `Verdict: CLEAR` **且基线一致**
5. 无合并/删分支动作，CLEAR 后输出最终结论即收尾

## 与 pr-review-loop 的差异

| 维度 | pr-review-loop | local-review-loop（本 skill） |
|---|---|---|
| 审核报告载体 | `gh pr comment` | 追加写入 `.review/REVIEW.md` |
| 审核上下文承载 | PR 的 commit + 评论 | `.review/REVIEW.md` 全部历史 |
| 结论锚定 | `Reviewed-Head`（HEAD SHA / `headRefOid`） | `Reviewed-Baseline`（被审文件集合的内容哈希指纹） |
| 收尾 | `gh pr merge` + 删分支 | 无合并；CLEAR 且基线一致即输出最终结论 |

## 前提条件

- **不要求处于 git 仓库**：适用于非 git 目录，或 git 仓库中不想/不便开 PR 的改动
- 代码改动已完成本地基础验证（按项目约定跑测试 / typecheck / build）；未通过前不进入流程
- 宿主支持启动子 agent（Agent 工具）
- `.review/REVIEW.md` 为过程记录，默认不纳入版本控制；是否入库由项目约定决定

## 使用方法

本流程**不自动触发**：仅当用户明确要求时执行——

- 「走本地审核闭环」「这些改动不上 git，走本地审核」
- 显式调用：Claude Code 中用 `/local-review-loop`；Codex 中在提示词里点名该 skill

进入流程前主 Agent 会做风险分级：

- **高风险**（DB 迁移、认证/额度、并发逻辑、路径处理与子进程、任务分发等）→ 完整循环（步骤 1 → 5）
- **低风险**（UI 细节、文案、文档、单文件小改）→ 单次审核：仅当报告无任何发现项时直接结束；存在任何未处置项（含建议修/仅供参考）就进入修复复审循环

拿不准时按高风险处理。

## 目录结构

单文件 skill：

```
local-review-loop/
└── SKILL.md      # 完整流程：范围圈定与基线、步骤 0–5、审核报告格式、反驳与再裁决、红线约束
```

## 注意

- 审核权归审核子 Agent；主 Agent 不得自我裁决「跳过」，反驳必须书面化并经审核子 Agent 再裁决。
- 修复提交后必须取得新基线上的 `Verdict: CLEAR`，旧基线上的 CLEAR 不算数。
- 流程内红线（不擅自收尾、不绕过审核规则、不改审核规则等）见 SKILL.md 文末。
