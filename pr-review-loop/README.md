# pr-review-loop — PR 审核闭环

修改方/审核方分离的 PR 审核全流程，`Verdict: CLEAR` 是唯一合并入口：

1. **主 Agent**：代码修改完成且本地基础验证通过后，建分支、创建中文标题 PR，启动审核子 Agent
2. **审核子 Agent**：以 PR 评论发布结构化审核报告（标号发现项 / 三级严重度 / `Verdict` 结论行），**不修改代码**
3. **主 Agent**：对每个发现项（含「建议修」「仅供参考」）逐项审视——合理即落地修复并逐项提交处理报告；不合理才书面反驳，经审核子 Agent 再裁决后跳过
4. 每轮新起复审子 Agent，循环至 `Verdict: CLEAR` **且 CI 全绿**
5. `gh pr merge` 合并并删除分支

## 前提条件

- 当前工作目录在 git 仓库内（`git rev-parse --is-inside-work-tree` 为 `true`）
- 代码改动已完成本地基础验证（按项目约定跑测试 / typecheck / build）；未通过前不建 PR
- `gh` CLI 已安装并登录（需 repo scope）；远端可用 CI
- 宿主支持启动子 agent（Agent 工具）

## 用法

- 本流程**不自动触发**：仅当用户明确要求时执行（点名本 skill，或明确说「走 PR 审核闭环」）
- 显式调用 `/pr-review-loop`
- 风险分级：高风险改动（DB 迁移、认证、并发、任务分发等）走完整循环；低风险改动（UI 细节、文案、文档、单文件小改）单次审核，报告无任何发现项才直接结束，有发现项仍进入修复复审循环

## 安装

```bash
git clone --depth 1 https://github.com/1010323691/MySkills.git
cp -r MySkills/pr-review-loop ~/.claude/skills/
```

Windows PowerShell：

```powershell
git clone --depth 1 https://github.com/1010323691/MySkills.git
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse "MySkills\pr-review-loop" "$HOME\.claude\skills\"
```

验证：`test -f ~/.claude/skills/pr-review-loop/SKILL.md && echo OK`，然后重启 Claude Code 或开新会话。

## 目录结构

单文件 skill：

```
pr-review-loop/
└── SKILL.md      # 完整流程：风险分级、步骤 0–5、审核报告格式、反驳与再裁决、红线约束
```

## 注意

- 审核权归审核子 Agent；主 Agent 不得自我裁决「跳过」，反驳必须书面化并经审核子 Agent 再裁决。
- 修复提交后必须取得新 HEAD 上的 `Verdict: CLEAR`，旧 HEAD 的 CLEAR 不算数。
- 流程内红线（不擅自合并、不改审核规则、不绕过 CI 等）见 SKILL.md 文末。
