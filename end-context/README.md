# end-context — 保存开发交接

> 安装方式见[仓库根 README](../README.md)（Claude 与 Codex 通用）。

## 用途

在大型软件项目中，当结束工作、切换 agent 窗口、准备交接或保存中途检查点时使用。它增量维护项目架构与功能、实际改动、待办、验证边界及命令失败经验，为下一位 agent 保存精简且可继续的上下文。

- 协议：`context-protocol/v2`（详见 `references/protocol.md`）
- 默认交接目录：`<项目根>/docs/agent-context/`；首次保存时只创建四个必需入口（README / PROJECT / CURRENT / ROUTES）和本次实际有内容的记录，不预建空模块
- **授权边界**：只维护交接文档；不修改业务代码、不提交/推送、不装依赖、不改数据库、不切分支、不管理后台服务
- 读侧（接手上下文）是 [start-context](../start-context/)，两者建议成对安装

## 使用方法

直接对 agent 说即可，无需命令，例如：

- 「保存一份开发交接」
- 「我要关这个窗口了，把上下文存好」
- 「存一个中途检查点，待会另一个窗口继续」

显式调用：Claude Code 中用 `/end-context`；Codex 中在提示词里点名该 skill（或让它按 description 自动触发）。

触发后的行为：

1. 对照本次要求、可见会话、开始基线、当前源码与真实命令结果，建立事实清单（区分本次修改 / 遗留改动 / 来源 unknown）
2. 采集分支 / HEAD / worktree、暂存 / 未暂存 / 未跟踪、已提交变化及未完操作
3. 记录停止点、恢复入口、验收缺口、阻塞；更新前先把已有 CURRENT 标为 partial
4. 按需更新模块、任务、正确命令、失败经验和长期决策（使用 `assets/templates/` 里的完整模板，缺信息写 unknown + 核实入口）
5. 写 session 记录；只有全局结构变化才改 PROJECT，只有导航变化才改 ROUTES / README
6. 可选运行 `scripts/context_check.py` 做只读结构检查（没有 Python 时用同等人工清单）
7. 最后生成 CURRENT：保存完整且已知未完项已记录标 `complete`，否则保持 `partial` 并说明缺口

完成后会简述更新路径、停止点、未完任务、保存完整性和实际持久化情况；落盘/检查失败时不会宣称交接成功。

## 目录结构

```
end-context/
├── SKILL.md                  # 正文：执行分支判断、执行顺序、约束
├── references/
│   ├── protocol.md           # 交接协议 context-protocol/v2
│   └── record-formats.md     # 记录填写规则
├── scripts/
│   └── context_check.py      # 只读结构检查（Python 3.9+，可选）
└── assets/
    └── templates/            # 10 个正文模板：README / PROJECT / CURRENT / ROUTES /
                              # MODULE / TASK / COMMAND / PITFALL / DECISION / SESSION
```

## 注意

- CURRENT 的 `complete` 只表示**此次交接保存完整**，不代表开发完成、测试全部通过或全项目已探索。
- `verified` 必须有相符范围的真实验证；症状（observed）、推断（inferred）、缺证据（unknown）分开标注，不合并。
- 不把全量对话 / diff / 日志写进文档；长期信息去重，过大记录按领域拆分并保留索引。
- 同一工作目录默认只有一个交接写入者；检测到共享目录已有写入者时按串行规则处理，不覆盖他人状态。
- 结构检查脚本只查文件、链接和基础字段，通过不代表语义准确或业务验收完成。
