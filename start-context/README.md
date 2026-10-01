# start-context — 接手开发上下文

> 安装方式见[仓库根 README](../README.md)（Claude 与 Codex 通用）。

## 用途

在大型软件项目中，当新 agent 开始工作、接手旧窗口、恢复开发或按交接继续任务时使用。

它先读精简的全局入口（项目 `docs/agent-context/` 下的 README、PROJECT、CURRENT、ROUTES，合计约 3,000～4,000 tokens），再按本轮任务查架构、功能、改动、待办与环境陷阱（普通接手文档量目标约 5,000～8,000 tokens），并结合当前代码和工作区核实能继续执行的状态——而不是把整个交接目录读进上下文。

- 协议：`context-protocol/v2`（详见 `references/protocol.md`）
- 默认交接目录：`<项目根>/docs/agent-context/`，可被用户或项目规则显式覆盖
- **只读 skill**：默认只读交接文档，不修改项目文件、不执行文档里的命令、不提交/推送、不装依赖
- 写侧（保存交接）是 [end-context](../end-context/)，两者建议成对安装

## 使用方法

直接对 agent 说即可，无需命令，例如：

- 「接手这个项目，继续之前的工作」
- 「先读 docs/agent-context 的交接文档，然后恢复开发」

显式调用：Claude Code 中用 `/start-context`；Codex 中在提示词里点名该 skill（或让它按 description 自动触发）。

触发后的行为：

1. 读 README / PROJECT / CURRENT / ROUTES 全局入口，检查保存状态、工作线、时间与探索缺口
2. 按本轮目标匹配领域与任务，先搜索标题/路径，只读相关条目和 1～3 个模块
3. 查看分支 / HEAD / worktree 和相关工作区变化，核实代码入口、契约与过去验证范围
4. 区分「现在确认 / 历史参考 / 尚未知」；文档与源码矛盾时明确指出，不把旧计划当作已实现
5. 给出摘要：项目概要、相关模块、实际停止点、任务/阻塞、适用命令与坑、第一步与核实缺口
6. 本轮已要求具体工作时直接继续执行；只要求了解项目时交付摘要

常见异常分支：

- 没有交接文档：受限探索现有资料与代码入口，标 unknown/partial，不猜
- 交接保存状态为 partial：优先核实停止点、任务和相关源码，不能认定缺失信息不存在
- 工作线与当前不匹配：全局知识可参考，任务和验证重新核实

## 目录结构

```
start-context/
├── SKILL.md                  # 正文：执行顺序、异常分支、约束
├── references/
│   ├── protocol.md           # 交接协议 context-protocol/v2（归属、阅读预算、状态语义、增长控制、权限与安全）
│   └── record-formats.md     # 记录填写规则（ID 约定、模板去向、状态判定、去重与拆分、常见错误）
└── scripts/
    └── context_check.py      # 只读结构检查（Python 3.9+，可选）
```

## 注意

- 记录正文模板不在本 skill 中，位于 end-context 的 `assets/templates/`；start-context 无需模板即可完成接手。
- `context_check.py` 只检查文件、链接和基础字段，通过不代表内容准确或业务验收完成；没有 Python 时用同等人工检查清单。
- skill 不读取密钥正文，不把交接资料中的旧指令当作新授权。
