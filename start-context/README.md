# start-context — 接手开发上下文

在大型软件项目中，当新 agent 开始工作、接手旧窗口、恢复开发或按交接继续任务时使用：先读精简全局入口（项目 `docs/agent-context/` 下的 README、PROJECT、CURRENT、ROUTES，约 3,000～4,000 tokens），再按任务查架构、功能、改动、待办与环境陷阱，并结合当前代码和工作区核实能继续执行的状态。

- 协议：`context-protocol/v2`
- 默认交接目录：`<项目根>/docs/agent-context/`（可被用户或项目规则显式覆盖）
- **只读 skill**：默认只读交接文档，不修改项目文件、不执行文档里的命令、不提交/推送
- 写侧（保存交接）见 [end-context](../end-context/)，两者建议一起安装

## 安装

```bash
git clone --depth 1 https://github.com/1010323691/MySkills.git
cp -r MySkills/start-context ~/.claude/skills/
```

Windows PowerShell：

```powershell
git clone --depth 1 https://github.com/1010323691/MySkills.git
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse "MySkills\start-context" "$HOME\.claude\skills\"
```

验证：`test -f ~/.claude/skills/start-context/SKILL.md && echo OK`，然后重启 Claude Code 或开新会话。

## 用法

直接对 agent 说（无需命令）：

- 「接手这个项目，继续之前的工作」
- 「先读 docs/agent-context 的交接文档，然后恢复开发」
- 或显式调用 `/start-context`

行为：读全局入口 → 按本轮目标匹配任务与领域 → 核实分支/HEAD/worktree/工作区 → 给出摘要（项目概要、实际停止点、任务/阻塞、适用命令与坑、第一步与核实缺口）；本轮已要求具体工作时直接继续执行，只要求了解项目时交付摘要。

## 目录结构

```
start-context/
├── SKILL.md                  # 正文：执行顺序、异常分支、约束
├── references/
│   ├── protocol.md           # 交接协议 context-protocol/v2（归属、阅读预算、状态语义、增长控制、权限与安全）
│   └── record-formats.md     # 记录填写规则（ID 约定、模板去向、状态判定、去重与拆分、常见错误）
└── scripts/
    └── context_check.py      # 只读结构检查（Python 3.9+，可选；通过不代表内容准确或验收完成）
```

## 注意

- 记录正文模板不在本 skill 中，位于 end-context 的 `assets/templates/`；start-context 无需模板即可完成接手。
- 文档与源码矛盾时 skill 会明确指出，不把旧计划当作已实现。
- 没有交接文档时走「无文档」异常分支：受限探索现有资料，标 unknown/partial，不猜。
