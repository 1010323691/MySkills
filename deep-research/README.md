# deep-research — 结构化深度研究

> 安装方式见[仓库根 README](../README.md)（Claude 与 Codex 通用）。

## 用途

用于调研、benchmark 对比、技术选型、竞品分析、文献综述等「帮我研究一下」类任务。走三阶段流水线：

1. **outline（初步调研）**：生成调研对象列表 + 字段框架，经确认后产出 `outline.yaml` / `fields.yaml`
2. **deep（并行深度调研）**：按批次分派子 agent 调研，每个对象输出结构化 JSON，并用验证脚本检查字段覆盖
3. **report（汇总报告）**：生成带目录、按字段分类详述和来源链接的 `report.md`

单事实查询（如「X 是哪年成立的」）不走此流水线：一轮搜索直接回答并给引用。

## 搜索通道

每次执行先检查并按优先级选定**一个**主通道、全程使用：

1. **Exa MCP（首选）**：环境里有 `web_search_exa` / `web_fetch_exa` 等 Exa 工具时使用，语义检索 + 直接返回正文，质量最高。遇 401/429 时提示用户完成 OAuth 或配置 API key，不静默降级。
2. **DuckDuckGo HTML（兜底，始终可用）**：用 `web_fetch` 类工具抓取 `https://html.duckduckgo.com/html/?q=<查询>` 并解析结果。
3. 默认不用 `curl` / `wget` / `requests` 等原始 HTTP 方式抓网页；例外：确认抓取通道不可用时，curl 可作最后兜底抓取**目标页面**（细节见 SKILL.md §0 第 3、4 条）。

## 依赖

- 宿主工具：`AskUserQuestion`、子 agent（Agent 工具）、`web_fetch` 类抓取工具
- Exa MCP（可选，推荐）；未安装时自动走 DuckDuckGo 兜底通道
- 无二进制依赖

## 使用方法

直接对 agent 说即可：

- 「帮我调研一下 XX 领域现状」
- 「对比 A、B、C 三个方案，做技术选型」
- 「竞品分析一下 XX」

显式调用：Claude Code 中用 `/deep-research`；Codex 中在提示词里点名该 skill（或让它按 description 自动触发）。

流程与产出（均位于工作目录下 `{topic_slug}/`）：

- 阶段 1：与你确认调研对象、字段框架和时间范围（会提问），生成 `outline.yaml`、`fields.yaml`
- 阶段 2：分批启动子 agent 并行调研，**每批完成需要你同意才进入下一批**；每个对象输出 `{item_slug}.json`（字段值中文，不确定值标 `[不确定]`），完成后跑 `validate_json.py` 校验字段覆盖
- 阶段 3：按你选择的摘要字段生成 `report.md`（目录 + 分类详情 + Sources + as-of 日期），以文件链接呈现

中途可随时要求补充调研对象或字段（追加到 yaml 文件、去重后继续）。

## 注意

- 阶段 2 使用并行子 agent 扇出（同一消息发多个 Agent 调用）；若宿主环境限制子 agent 并发数（例如全局约定同时只允许 1 个），执行前应把批内并行改为串行并相应调小 `batch_size`，其余流程不变。
- 相对时间（「最近」「近 6 个月」）一律先按当前环境日期换算成精确日期并显式写出。
- 关键事实多源交叉验证；源间冲突时明确写出差异，区分「事实」与「观点/推测」。
- 除非覆盖经过验证，不使用「exhaustive / 完整列表」措辞，默认「尽力而为的发现」。
