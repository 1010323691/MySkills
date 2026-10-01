# deep-research — 结构化深度研究

用于调研、benchmark 对比、技术选型、竞品分析、文献综述等「帮我研究一下」类任务。三阶段流水线：

1. **outline（初步调研）**：生成调研对象列表 + 字段框架，与用户确认后产出 `outline.yaml` / `fields.yaml`
2. **deep（并行深度调研）**：按批次分派子 agent 并行调研，每个对象输出结构化 JSON，并用验证脚本校验字段覆盖
3. **report（汇总报告）**：生成带目录、按字段分类详述和来源链接的 `report.md`

单事实查询不走此流水线（一轮搜索直接回答并给引用）。

## 搜索通道（每次执行先检查，全程用同一主通道）

1. **Exa MCP（首选）**：工具列表中存在 `web_search_exa` / `web_fetch_exa` 等 Exa 工具时使用；遇 401/429 时提示用户完成 OAuth 或配置 API key，不静默降级。
2. **DuckDuckGo HTML（兜底，始终可用）**：用 `web_fetch` 类工具抓取 `https://html.duckduckgo.com/html/?q=<查询>` 并解析结果。
3. 硬性禁止用 `curl`/`wget`/`requests` 等原始 HTTP 方式抓网页。

## 依赖

- 宿主工具：`AskUserQuestion`、`Agent`（子 agent）、`web_fetch` 类抓取工具
- 可选：Exa MCP（推荐，质量最高）；未安装时自动走 DuckDuckGo 兜底通道
- 无二进制依赖

## 安装

```bash
git clone --depth 1 https://github.com/1010323691/MySkills.git
cp -r MySkills/deep-research ~/.claude/skills/
```

Windows PowerShell：

```powershell
git clone --depth 1 https://github.com/1010323691/MySkills.git
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse "MySkills\deep-research" "$HOME\.claude\skills\"
```

验证：`test -f ~/.claude/skills/deep-research/SKILL.md && echo OK`，然后重启 Claude Code 或开新会话。

## 用法

直接对 agent 说：

- 「帮我调研一下 XX 领域现状」
- 「对比 A、B、C 三个方案，做技术选型」
- 或显式调用 `/deep-research`

产出（位于工作目录下 `{topic_slug}/`）：`outline.yaml`、`fields.yaml`、每个调研对象的 `{item_slug}.json`（含 `uncertain` 字段清单）、最终 `report.md`（标注 as-of 日期，来源逐条列出）。

## 注意

- 正文的阶段 2 使用**并行子 agent 扇出**（同一消息发多个 Agent 调用）；若宿主环境限制子 agent 并发数（例如全局约定同时只允许 1 个），执行前应把批内并行改为串行、相应调小 `batch_size`，其余流程不变。
- 相对时间（「最近」「近 6 个月」）一律先按当前环境日期换算成精确日期并显式写出。
- 不确定值标注 `[不确定]` 并汇总到 JSON 的 `uncertain` 数组，报告中跳过。
- 除非覆盖经过验证，不使用「exhaustive / 完整列表」措辞，默认「尽力而为的发现」。
