# pr-review-loop — PR 审核闭环

在用户明确要求执行闭环时，完成创建或接手 PR、独立审核、逐项修复/反驳、复审、合并和安全清理。主 Agent 修改，审核子 Agent 只审核与评论；全部发现都要处理，`Verdict: CLEAR` 绑定完整 HEAD SHA。

## 使用

例如：「对这个 PR 走审核闭环」，或「用 `$pr-review-loop` 完成当前改动的 PR 闭环」。仅询问、评审或优化技能本身，不启动此流程。用户指定只审核、不推送或不合并时遵守限定范围。

完整闭环授权范围内的提交、推送、PR 评论、合并及本轮分支安全清理，均由主 Agent 自动执行，无需逐步确认，也不交给用户手动合并或删分支。低风险可以一轮收敛，仍须完成全部合并门禁与实际合并确认。

## 依赖与门禁

- Git 仓库、明确的 GitHub 远端，已登录且具备所需权限的 `gh`。
- 宿主支持独立子 Agent；验证使用项目 `AGENTS.md` / `CLAUDE.md` 等约定。
- Python 3（运行 `scripts/pr_state.py`；Windows 用 `python`）。
- 审核子 Agent 无权发布评论时，由主 Agent 校验 sha256 后原样代发并标注来源。
- 当前 HEAD 的独立 CLEAR、所有发现独立核销/裁决、适用 CI 通过和仓库保护满足后才合并。确实无适用 CI 时记录不适用；空检查或未知状态不算通过。
- 合并使用 `--match-head-commit` 防止审核后提交竞态。入队不等于已合并；实际合并后才安全清理本轮专用分支，已有共享分支默认保留。

## 文件

```text
pr-review-loop/
├── SKILL.md                         流程总览、授权、审核、逐项处理、合并门禁与清理
├── scripts/pr_state.py              只读汇总门禁事实：完整 HEAD、全部 Verdict 及绑定 SHA、CI 分桶、可机械判定的阻塞项
├── references/reviewer-brief.md     每轮启动审核子 Agent 的任务书模板（只给事实，不给结论）
├── references/report-templates.md   审核/处理报告模板、代发格式与 CLI 依据
├── references/merge-queue.md        合并队列与自动合并的异步风险处理
├── agents/openai.yaml               Codex：仅显式调用
└── evals/evals.json                 隔离决策模拟回归场景
```

安装方式见[仓库根 README](../README.md)。Codex 的显式调用策略由 `agents/openai.yaml` 表达；其他宿主仍需遵守技能正文的执行授权边界。
