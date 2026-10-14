# local-review-loop — 本地审核闭环（无 PR 介质）

> 安装方式见[仓库根 README](../README.md)（Claude 与 Codex 通用）。规则以 [SKILL.md](SKILL.md) 为准，本文件只说明用途与依赖。

## 用途

修改方/审核方分离的**本地**审核闭环，与 [pr-review-loop](../pr-review-loop/) 共用审核协议（三级分级、稳定编号、逐项处置、反驳再裁决、续用/新起审核者），差异只在审核介质：不建分支、不建 PR、不等 CI、不合并。适用于代码不上 git，或在 git 仓库但不想/不便开 PR 的改动。

| 维度 | pr-review-loop | local-review-loop |
|---|---|---|
| 审核记录 | PR 评论 | 追加写入 `.review/REVIEW.md` |
| 结论锚定 | `Reviewed-Head`（HEAD SHA） | `Reviewed-Baseline`（被审文件集合的内容指纹） |
| 增量 diff | `git diff` | `scripts/review_state.py diff`（基于每轮快照） |
| 收尾 | 合并 + 清理分支 | CLEAR 且指纹一致即写最终结论 |

## 使用

仅在用户明确要求时执行，例如「走本地审核闭环」「这些改动不上 git，走本地审核」，或点名本技能；一经启动直接进入流程，不反问。改完代码不会自动触发。

## 依赖

- 宿主支持独立子 Agent（Claude Code 的 `Agent` / `SendMessage`，或 Codex 子 Agent）。
- Python 3（运行 `scripts/review_state.py`；Windows 用 `python`）。
- 可选：`code-review` 技能（自检；不可用时退化为人工通读）。
- `.review/` 为过程记录，默认不入库（git 仓库中加入 `.git/info/exclude`）。

## 文件

```text
local-review-loop/
├── SKILL.md                       主 Agent 流程：授权、准备与自检、范围与基线、复审方式、逐项处理、收尾
├── scripts/review_state.py        基线指纹、快照、增量 diff、结论绑定核对（只写 .review/）
├── scripts/test_review_state.py   脚本测试（临时目录）
├── references/reviewer-guide.md   审核子 Agent 规程与审核报告模板
└── evals/evals.json               隔离决策模拟场景
```
