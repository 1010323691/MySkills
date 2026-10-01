---
name: "deep-research"
description: "结构化深度研究三阶段流水线（outline→并行deep→report）+ Exa MCP 优先/DuckDuckGo 兜底搜索。用于调研、benchmark对比、技术选型、竞品分析、文献综述等\"帮我研究一下\"任务。"
---

# Deep Research（结构化深度研究）

Use when the user asks for 调研 / 深度研究 / benchmark 调研 / 技术选型 / 竞品分析 / 文献综述 / "research this" / "deep dive" / 多对象多维度研究. Single-fact lookups are NOT deep research — for those, run one search round and answer directly with citations.

融合自：Weizhena/Deep-Research-skills（三阶段流水线：outline → deep → report，MIT）+ exa-labs/exa-mcp-server 官方 search/exa-agent 方法论。

## 0. 搜索通道选择（每次先检查）

按优先级选择并全程使用同一主通道：

1. **Exa MCP（首选）**：若工具列表中存在 `web_search_exa` / `web_fetch_exa` / `web_search_advanced_exa` / `agent_run`（工具名前缀因客户端而异，如 `mcp__exa__web_search_exa`）则用 Exa：语义检索 + 直接返回正文，质量最高。
   - Exa 认证：OAuth（首选）> API key（dashboard.exa.ai/api-keys，经 `?exaApiKey=` 或 `Authorization: Bearer`）> 匿名（有速率限制）。
   - 遇到 401/429 时：明确告诉用户需要 OAuth 登录或配置 key，不要静默降级到通用搜索。
2. **DuckDuckGo HTML（兜底，始终可用）**：用 `mcp__workspace__web_fetch` 抓 `https://html.duckduckgo.com/html/?q=<URL编码查询>`（备用 `https://lite.duckduckgo.com/lite/?q=`）。解析：标题在 `<h2 class="result__title">`，真实 URL 是结果链接中 `uddg=` 参数 URL 解码，摘要在 `a.result__snippet`，日期为 ISO 格式的 `<span>`。支持 `kl=<region>`（jp-jp、cn-zh 等）与 `df=` 时间过滤（d/w/m/y）。目标页面直接用 web_fetch 抓取；超大页面会落盘为 txt，用 bash/python 按字符范围切片提取关键部分（如 `<title>`、正文段落）。落盘后再用原生解释器（python/node）处理时：Windows 下 Git Bash 的 `/tmp` 不是原生解释器的 `/tmp`，必须传宿主绝对路径，并在解析前确认文件存在、检查大小。
3. **原始 HTTP 原则与例外**：默认不用 bash 的 curl/wget/lynx 或 Python requests 等原始 HTTP 方式抓网页（让搜索与抓取留在可审计的通道内）；某域名抓取失败时换信源，不得换通道绕过。例外：抓取通道被确认不可用（见第 4 条）时，可用 curl 作最后兜底抓取**目标页面**（不是搜索结果页），次数以够用为限，并在报告中明确注明降级。
4. **通道故障判定（先判错误来源，再定动作）**：
   - 工具链错误（宿主搜索/抓取工具报内部错误：缺 schema/executor、抓取服务 4xx/5xx、模板/渲染错误等）→ 该通道当前不可用；同一工具不重试超过 2 次，按「专用搜索工具 → web_fetch 抓搜索页 → curl 落盘**目标页面**本地解析（搜索页仍限 web_fetch，见第 3 条例外）」顺序降级，并在报告中注明通道异常（Exa 401/429 仍按第 1 条：提示用户认证，不静默降级）。
   - 页面级失败（404、超时、空响应、反爬）→ 换信源，保持通道。
   - web_fetch 类工具通常不自动跟随跨域重定向（返回重定向 URL 而非内容）：拿到目标后手动再取一次；重定向目标本身也报工具链错误时，判抓取通道不可用，转第 3 条的 curl 兜底。
   - 落盘文件读不到：先核对路径与工具链差异（第 2 条的 Windows `/tmp` 坑），不要误判为抓取失败。

## 1. 日期计算（先做）

查询含相对时间（"最近"、"近6个月"、"post-IPO"）时，先用当前环境日期算出精确日期并显式写出计算过程。禁止估算或沿用示例中的日期。

## 2. 三阶段流水线（完整深度研究）

### 阶段 1：outline（初步调研）
1. 用模型已有知识生成两项：items 列表（调研对象）与字段框架（常见分类：基本信息 / 技术特性 / 性能指标 / 里程碑意义 / 商业信息 / 竞争与生态 / 历史沿革 / 市场定位）。用 AskUserQuestion 确认：items 是否增删、字段是否满足、时间范围（近6个月 / 2024年至今 / 不限）。
2. 启动 1 个搜索子 agent（Agent 工具，可用后台），prompt 严格按此模板（只替换 {变量}）：
   ```
   ## 任务
   调研话题: {topic}
   当前日期: {YYYY-MM-DD}
   基于以下初步框架，补充最新items和推荐调研字段。
   ## 已有框架
   {outline框架内容}
   ## 目标
   1. 验证已有items是否遗漏重要对象  2. 补充遗漏对象
   3. 搜索{topic}相关且{time_range}内的items并补充  4. 补充新fields
   ## 搜索方法
   {第0节选定的搜索通道及用法}
   ## 输出要求（直接返回，不写文件）
   ### 补充Items
   - item_name: 简要说明（为什么应加入）
   ### 推荐补充字段
   - field_name: 字段描述（为什么需要该维度）
   ### 信息来源
   - [来源](url)
   ```
3. 询问用户是否有已定义的字段文件，有则读取合并。
4. 生成两个文件到 `{topic_slug}/`：
   - `outline.yaml`：topic、items[]（name/category/description）、execution{batch_size, items_per_agent, output_dir}（batch_size 与 items_per_agent 用 AskUserQuestion 确认）。
   - `fields.yaml`：字段分类 + 每字段 name/description/detail_level（极简/简要/详细）+ uncertain 保留字段列表。
5. 展示给用户确认后才进入阶段 2。

支持中途补充：用户可随时要求补 items / 补字段 —— 追加到对应 yaml 文件（去重），确认后再继续。

### 阶段 2：deep（并行深度调研）
1. 定位 `outline.yaml`；断点续传：检查 output_dir 已存在的 `{item_slug}.json` 则跳过。
2. 先写验证脚本 `{topic_slug}/validate_json.py`：读取 fields.yaml 与目标 JSON，检查所有必填字段覆盖（扁平或嵌套结构都要能定位字段），缺失字段则打印清单并非零退出；`[不确定]` 值仅作警告。
3. 按 batch_size 分批（每批完成需用户同意才进行下一批）。每批内并行启动子 agent（同一消息发多个 Agent 调用；简单任务可指定 model: "haiku"），每个子 agent 负责 items_per_agent 个 item，prompt 严格按模板：
   ```
   ## 任务
   调研 {item_related_info}，输出结构化JSON到 {output_path}
   ## 字段定义
   读取 {fields_path} 获取所有字段定义
   ## 搜索方法
   {第0节选定的搜索通道}。每个 item 生成 3–5 个不同角度的查询（改变视角而非同义词）；对关键页面抓全文核对，不要只看摘要。
   ## 信源路由
   官方文档/发布说明/官方博客优先；调试类 → GitHub Issues + Stack Overflow；学术类 → arXiv/Semantic Scholar；中文生态 → 知乎/掘金/CSDN/OSChina；最佳实践 → 官方博客/HN/Reddit。
   ## 输出要求
   1. 按fields.yaml字段输出JSON  2. 不确定值标注[不确定]
   3. JSON末尾加 uncertain 数组列出所有不确定字段名
   4. 字段值使用中文（调研过程可用英文）
   5. JSON末尾加 sources 数组：[{title, url}]，只列关键证据（不倾倒全量链接）
   ## 验证
   完成后运行 python {topic_slug}/validate_json.py -f {fields_path} -j {output_path}，通过才算完成。
   ```
4. 监控每批完成，展示进度；全部完成后汇总：完成数、失败/含不确定项的 items、输出目录。

### 阶段 3：report（汇总报告）
1. 用 AskUserQuestion 问用户目录中除 item 名称外还要展示哪些摘要字段（从实际 JSON 中提取数值型/短指标字段作为动态选项，如 stars、citations、release_date、valuation）。
2. 生成 `{topic_slug}/generate_report.py`，要求：
   - 读取 output_dir 全部 JSON + fields.yaml；兼容扁平与嵌套结构（顶层 → category key → 遍历嵌套 dict）；category 中英名双向映射（如 基本信息↔basic_info、技术特性↔technical_features、性能指标↔performance_metrics、商业信息↔business_info、竞争与生态↔competition_ecosystem、里程碑意义↔milestones、历史沿革↔history、市场定位↔market_positioning，未命中的按实际 key 自适应）。
   - 跳过：值含 `[不确定]`、字段名在 uncertain 数组、值为 null/空。
   - 格式：目录（每个 item 必须出现：序号 + 名称锚点链接 + 用户选定的摘要字段，示例 `1. [GitHub Copilot](#github-copilot) - Stars: 10k | Score: 85%`）+ 按字段分类的详细内容 + 末尾「Sources」节（汇总各 item JSON 的 sources 数组并去重，标签逐条链接）。
   - 复杂值格式化：list-of-dicts 每项一行用 ` | ` 分隔 kv；长列表换行；>100 字符的长文本用 `<br>` 或 blockquote。
   - 未定义字段收进"其他信息"分类（过滤内部字段 `uncertain`、`_source_file` 及嵌套结构的顶级 category key）。
3. 运行脚本生成 `{topic_slug}/report.md`，用 present_files / computer:// 链接呈现给用户。

## 3. 子 agent 搜索方法论（所有搜索子 agent 必须遵守）

- 每个子任务生成 5–10 个查询变体：新手 vs 专家术语、问题本身 + 解决方案、报错信息加引号原文、版本号与环境细节；实际从中挑选 3–5 个变体执行搜索调用（与阶段模板的单 item 预算一致），不必全部跑完。
- 不只看前几条结果；交叉核对日期，注明已过时的方案；区分官方解决方案与社区 workaround；标注实验性/未验证内容。
- 多源交叉验证关键事实；源间冲突时明确写出差异；区分"事实"与"观点/推测"。
- 输出格式：调用方指定格式优先；未指定时用：执行摘要（2–3 句）→ 详细发现（按方案/主题分节，含来源链接、代码/配置示例、版本要求）→ **Sources（永远必须有**，`[标题](URL)` 逐条列出）→ 建议 → 备注（存疑/需进一步研究）。
- 信息不足时：说明搜了什么、局限在哪、建议去哪个社区/渠道问。

## 4. Exa 高级编排（仅当 Exa MCP 可用时）

- **上下文隔离**：原始搜索结果不得进入主上下文——用子 agent 承接检索，只回传提炼后的紧凑结果。每个子 agent 末尾按原文输出 `sources_reviewed: N`（N = 该 agent 所有 web_search_exa 调用的 numResults 之和，含重试）。
- **规模控制**：每子 agent **每 item** 3–5 次搜索调用（items_per_agent>1 时按 item 累加，不是整个 agent 的总上限；与阶段 2 模板「每 item 3–5 个查询」一致）；本节适用于 Exa 多轮/多子 agent 编排（含阶段 2 分批），搜索通道本身仍按 §0 选择；独立工作流并行分发（同一消息）；同一消息发出全部子 agent 后等待结果，不用后台。
- **汇总**：先按 URL 去重（同一实体不同源则合并字段取最完整/最新）；检查覆盖缺口（时间段/地区/实体类型），针对性补搜；开头写 "使用 Exa 审阅了 {X} 个来源（跨 {Y} 个子 agent）"。
- **多轮（multi-pass）**：实体链式（先找公司再找人物再找言论）、先探路后深挖、标准发现式；每轮之间先汇总去重再开下一轮。
- **信源质量**：高信号来源（实践者、有 stake 的人）的收敛才有意义；实践者 > 评论者；先定义排除名单（利益错位/无法证伪的来源）；对汇总结果做红队检查（缺什么视角？有什么偏差？）。专家/最佳实践类问题：先给"优秀来源的一致结论"，再引用谁说的。
- **agent_run（列表构建/结构化输出）**：先写下 objective、universe、segments、coverage target、output fields、evidence requirements、exclusions，再建 run。outputSchema 规则：顶层 object，行数据放具名数组，加 maxItems，必含证据字段（url/日期/confidence）与稳定标识符（域名/ticker/LinkedIn），模糊判断加 confidence 字段。`status: "running"` 时用 runId 轮询直到 `outputReady`。
- **覆盖度措辞**：除非 universe 有界、覆盖验证过、去重并检查过证据，否则不得声称 "exhaustive/all/完整列表"；默认用 "best-effort discovery（尽力而为的发现）"、"非穷尽"、"X 方向覆盖较强、Y 方向较弱"。

## 5. 输出与呈现

- 中文回答；大调研先给一屏内摘要（Result 直接答案 / Process 高信号与已过滤掉的 / Patterns 非显而易见的模式 / Notes 与用户工作相关的附带发现），完整内容写文件（report.md、必要时 .csv）并给链接。
- 表格优先于列表；链接化有价值的实体名；无 emoji（除非用户要求）。
- 报告标注 as-of 日期。

## 6. 陷阱清单

- 简单问题过度执行（"X 是哪年成立的" 不需要子 agent）；复杂多约束问题执行不足（≥4 个约束/时间连接/语义过滤必须 fan out）。
- 同义查询浪费 token（改变角度，不是换词）。
- 忘记去重；把搜索结果当已验证事实（相似 ≠ 合格，必须验证）。
- 日期漂移（一律以当前环境日期为准）。
- 子 agent 返回空：换角度重写查询，仍空则该主题网络覆盖有限——如实报告。返回跑题：查询太泛，加长、加具体约束重试。
- 混淆错误来源：把抓取服务的内部工具链错误（缺 schema/executor、4xx/5xx、模板渲染错误）当目标页面问题反复重试同一工具——先判错误来源；工具链错误最多重试 2 次即降级（§0 第 4 条）。
- 假定 web_fetch 自动跟随重定向：跨域重定向返回的是 URL 而非内容，且重定向目标本身可能失败——准备好 curl 兜底。
- Windows 路径错位：bash 的 `/tmp`（→ AppData\Local\Temp）与原生解释器的 `/tmp`（→ 盘符根目录）不是同一处，跨工具链处理时文件“消失”——统一用宿主绝对路径。
- 文档站解析：大 HTML 内嵌整棵文档树与导航菜单，同一内容多处出现——剥离 script/style 后按关键词开窗提取并去重；终端回显乱码（GBK 控制台 vs UTF-8 内容）时以显式 UTF-8 读文件为准。

