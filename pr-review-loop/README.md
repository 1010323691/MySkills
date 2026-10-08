# pr-review-loop — PR 审核闭环

在用户明确要求执行闭环时，完成创建或接手 PR、独立审核、逐项修复/反驳、复审、合并和安全清理。主 Agent 修改，审核子 Agent 只审核与评论；全部发现都要处理，`Verdict: CLEAR` 绑定完整 HEAD SHA。

## 使用

例如：「对这个 PR 走审核闭环」，或「用 `$pr-review-loop` 完成当前改动的 PR 闭环」。仅询问、评审或优化技能本身，不启动此流程。用户指定只审核、不推送或不合并时遵守限定范围。

完整闭环授权范围内的提交、推送、PR 评论、合并及本轮分支安全清理，无需逐步确认。低风险可以一轮收敛，仍须完成全部合并门禁与实际合并确认。

## 依赖与门禁

- Git 仓库、明确的 GitHub 远端，已登录且具备所需权限的 `gh`。
- 宿主支持独立子 Agent；验证使用项目 `AGENTS.md` / `CLAUDE.md` 等约定。
- 当前 HEAD 的独立 CLEAR、所有发现独立核销/裁决、适用 CI 通过和仓库保护满足后才合并。确实无适用 CI 时记录不适用；空检查或未知状态不算通过。
- 合并使用 `--match-head-commit` 防止审核后提交竞态。入队不等于已合并；实际合并后才安全清理本轮专用分支，已有共享分支默认保留。

## 文件

```text
pr-review-loop/
├── SKILL.md                       授权、审核、逐项处理和合并门禁
├── agents/openai.yaml             Codex：仅显式调用
├── references/report-templates.md 审核/处理报告模板与 CLI 依据
└── evals/evals.json               隔离决策模拟回归场景
```

安装方式见[仓库根 README](../README.md)。Codex 的显式调用策略由 `agents/openai.yaml` 表达；其他宿主仍需遵守技能正文的执行授权边界。
