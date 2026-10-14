# pr-review-loop — PR 审核闭环

在用户明确要求执行闭环时，完成创建或接手 PR、提交前自检、独立审核、逐项修复/反驳、复审、合并和安全清理。主 Agent 修改，审核子 Agent 只审核与评论；`Verdict: CLEAR` 绑定完整 HEAD SHA。规则以 [SKILL.md](SKILL.md) 为准，本文件只说明用途与依赖。

## 使用

例如：「对这个 PR 走审核闭环」，或「用 `$pr-review-loop` 完成当前改动的 PR 闭环」。仅询问、评审或优化技能本身，不启动此流程。一经启动直接进入流程，不反问用户；用户限定只审核、不推送或不合并时遵守限定范围。

## 依赖

- Git 仓库、明确的 GitHub 远端，已登录且具备所需权限的 `gh`。
- 宿主支持独立子 Agent（Claude Code 的 `Agent` / `SendMessage`，或 Codex 子 Agent）。
- Python 3（运行 `scripts/pr_state.py`；Windows 用 `python`）。
- 可选：`code-review` 技能（提交前自检；不可用时退化为人工通读 diff）。
- 宿主拒绝合并命令时（如 Claude Code 自动模式对无正式 review 的 PR），由用户执行交接的精确合并命令，其余步骤仍在会话内完成。

## 文件

```text
pr-review-loop/
├── SKILL.md                         主 Agent 流程：授权、宿主适配、准备与自检、复审方式、逐项处理、合并门禁与清理
├── scripts/pr_state.py              只读汇总门禁事实：完整 HEAD、全部 Verdict（含格式/编辑校验）、CLEAR 后改动、CI 与适用性、可合并性
├── references/reviewer-guide.md     审核子 Agent 规程：取证、定级、结论格式、发布与复审
├── references/reviewer-brief.md     新起 / 续用审核者的任务书模板（只给事实，不给结论）
├── references/report-templates.md   审核报告、处理报告、仅供参考处置记录与代发格式
├── references/merge-queue.md        合并队列与自动合并的异步风险处理
├── agents/openai.yaml               Codex：仅显式调用
└── evals/evals.json                 隔离决策模拟回归场景
```

安装方式见[仓库根 README](../README.md)。Codex 的显式调用策略由 `agents/openai.yaml` 表达；其他宿主仍需遵守技能正文的执行授权边界。
