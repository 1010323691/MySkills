# tool-call-pitfalls — 工具调用陷阱同步

> 安装方式见[仓库根 README](../README.md)（Claude 与 Codex 通用）。

## 用途

记录并同步「工具调用陷阱」（无法被 Agent 识别、无法执行的工具），保持两处存放、四个文件一致：

| 角色 | 路径 |
|------|------|
| 单一事实源（仓库） | 仓库根 `tool-call-pitfalls.md` |
| 派生视图（仓库） | 仓库根 `CLAUDE.md`（「工具调用陷阱」一节的工具清单） |
| 派生视图（记忆） | `~/.claude/projects/D--projectPath-MySkills/memory/tool-call-pitfalls.md` |
| 索引（通常不动） | `~/.claude/projects/D--projectPath-MySkills/memory/MEMORY.md` |

为什么费这个劲维护两处：仓库文件给人看、长期留存；个人记忆由每次会话自动加载，作用是让模型不再按 Claude Code 默认工具集的先验去调用死工具。一边更新了另一边没跟上，下次会话还是会踩同一个坑。

## 三种模式

- **新增/更新**：新出现不可用工具，或用户指出刚发生的某次调用就是陷阱 → 备齐五要素（工具名、现象、环境、替代方案、系统日期）→ 同步四个文件 → 提交推送
- **移除**：某已记录陷阱在某个环境已可用 → 默认**保留条目、补充观察**（可用性按 harness/版本变化，不删结论）；只有用户明确说删才整条删除
- **核对**：纯只读漂移报告（不写不提交），用户确认后再按对应流程修复

## 使用方法

用户点名触发（不自动触发）：「某工具不可用/调用失败」「你刚做的那次调用就是典型陷阱」「记录/同步一个陷阱」「某陷阱现在可用了」「核对两处记录是否一致」。加「先不提交/dry run」时只展示各文件 diff、不提交，等用户确认。

## 前提条件

- MySkills 仓库位于 `D:\projectPath\MySkills`，git 远端 origin 可 push
- 个人记忆目录为 `~/.claude/projects/D--projectPath-MySkills/memory/`
- **路径绑定本机**：换机器安装前需先改 `SKILL.md` 开头的路径表

## 目录结构

```
tool-call-pitfalls/
├── README.md
├── SKILL.md        # 完整流程：文件角色、模式判定、新增/更新/移除/核对、边界情况
└── evals/
    └── evals.json  # 三个测试案例：dry-run 新增、补充观察（真实数据）、只读核对
```

## 注意

- 日期用 Bash `date +%F` 取系统日期，不信任会话上下文里的日期
- `git add` 只加 `tool-call-pitfalls.md` 与 `CLAUDE.md` 两个文件，工作区其他改动不动
- 记忆文件 frontmatter 中应用维护的字段（`node_type`/`originSessionId`/`modified` 等）原样保留，只动 `description` 与正文
- `push` 失败时保留本地 commit、如实报告，重试交给用户
