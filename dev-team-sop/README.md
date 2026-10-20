# dev-team-sop

软件开发团队 SOP，Claude Code 原生版：主会话当主理人，用 `Agent` 工具派出产品经理 / 架构师 / 工程师 / QA 四个子代理，产出落盘、按文件交接；按需求规模路由到快速模式 / BugFix / 标准 SOP / 增量开发 / 部分工作流。

## 来源
依据 WorkBuddy 专家团 **software-company v1.1.0** 的原版角色与流程（`plugin.json` + 5 个角色模板）提炼，并完全改写为 Claude Code 的机制：子代理定义、`Agent` / `SendMessage`、文件交接、`NEED-INPUT:` 与 `Routing:` 约定。不含任何运行会话里的内容。

## 目录
```
SKILL.md                              主理人手册：铁律、路由、各工作流、QA 闭环、派工与续接方法、交付汇报
agents/software-product-manager.md    产品经理   PRD 简/完整 + 市场调研
agents/software-architect.md          架构师       系统设计 + ≤5 个任务的分解
agents/software-engineer.md           工程师     一次写完 + 硬约束 + 全局自审 IS_PASS
agents/software-qa-engineer.md        QA           测试 + 智能路由 + 最多 2 轮 + 报告
evals/evals.json                      决策模拟用例（18 条，未用子 Agent 实跑）
```

## 使用
直接说「用软件开发团队 / 走 SOP 做 XXX」即可触发。skill 会按 SKILL.md 派工。

**可选：安装为原生子代理**（之后 `Agent` 可直接用 `subagent_type: "software-architect"` 等；不安装也能用，主理人会改用 `general-purpose` 并内嵌章程）：

```bash
mkdir -p ~/.claude/agents
cp dev-team-sop/agents/*.md ~/.claude/agents/
```

只想在某个项目里用，就复制到该项目的 `.claude/agents/`。新装的子代理需要重开会话才会出现在可选类型里。

## 模型
不指定模型：四个成员都跟随主会话当前模型。

## 约定速查
- 交接目录：`docs/`（`prd.md`、`system_design.md`、`sequence-diagram.mermaid`、`class-diagram.mermaid`、`test-report.md`）
- 成员回复：产出路径 + ≤15 行摘要；缺输入时首行 `NEED-INPUT:`
- QA 报告末行：`Routing: Engineer | QA | NoOne`
- 工程师回报：`IS_PASS: YES/NO`
- 续接成员：记下 `Agent` 返回的 agent ID，用 `SendMessage`（需先 `ToolSearch` 载入）
