# context-end — 保存开发交接

在大型软件项目中，当结束工作、切换 agent 窗口、准备交接或保存中途检查点时使用：增量维护项目架构与功能、实际改动、待办、验证边界及命令失败经验，为下一位 agent 保存精简且可继续的上下文。

- 协议：`context-protocol/v2`
- 默认交接目录：`<项目根>/docs/agent-context/`（首次保存时创建四个必需入口 README/PROJECT/CURRENT/ROUTES，其余记录按需创建）
- **授权边界**：只维护交接文档；不修改业务代码、不提交/推送、不装依赖、不改数据库、不切分支
- 读侧（接手上下文）见 [context-start](../context-start/)，两者建议一起安装

## 安装

```bash
git clone --depth 1 https://github.com/1010323691/MySkills.git
cp -r MySkills/context-end ~/.claude/skills/
```

Windows PowerShell：

```powershell
git clone --depth 1 https://github.com/1010323691/MySkills.git
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse "MySkills\context-end" "$HOME\.claude\skills\"
```

验证：`test -f ~/.claude/skills/context-end/SKILL.md && echo OK`，然后重启 Claude Code 或开新会话。

## 用法

直接对 agent 说（无需命令）：

- 「保存一份开发交接」
- 「我要关这个窗口了，把上下文存好」
- 或显式调用 `/context-end`

行为：建立事实清单 → 采集分支/HEAD/worktree/未提交变化 → 更新模块/任务/命令/坑/决策（按模板）→ 写 session 记录 → 可选运行 `scripts/context_check.py` 做只读结构检查 → 最后生成 CURRENT（保存完整标 `complete`，有缺口保持 `partial`）。

## 目录结构

```
context-end/
├── SKILL.md                  # 正文：执行分支判断、执行顺序、约束
├── references/
│   ├── protocol.md           # 交接协议 context-protocol/v2
│   └── record-formats.md     # 记录填写规则
├── scripts/
│   └── context_check.py      # 只读结构检查（Python 3.9+，可选；检查失败时也可用同等人工清单）
└── assets/
    └── templates/            # 10 个正文模板：README/PROJECT/CURRENT/ROUTES/MODULE/TASK/
                              # COMMAND/PITFALL/DECISION/SESSION
```

## 注意

- CURRENT 的 `complete` 只表示**此次交接保存完整**，不代表开发完成、测试全部通过或全项目已探索。
- `verified` 必须有相符范围的真实验证；症状（observed）、推断（inferred）、缺证据（unknown）分开标注。
- 同一工作目录默认只有一个交接写入者；检测到共享目录已有写入者时按串行规则处理，不覆盖他人状态。
- 结构检查脚本只查文件、链接和基础字段，通过不代表语义准确或业务验收完成。
