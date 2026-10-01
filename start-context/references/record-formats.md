# 记录填写规则

## 固定规则

- 文件正文模板位于 end-context 的 assets/templates/；start-context 无需依赖这些文件才能接手。
- 生成正式记录时替换所有尖括号占位符。信息缺失写 unknown + 核实入口；不适用写 not_applicable + 原因。
- ID 只用字母、数字和连字符。任务 T-、模块 M-、命令 C-、坑 P-、决策 D-、session S-。
- 生成 ID 时使用 UTC 时间戳和短随机串，例如 S-20261001T082000Z-a1b2c3；记录可读时间带时区。
- 同一记录 ID 始终不变；新记录先搜索冲突。重复执行同一检查点，继续更新该 session 草稿，不制造相同内容的重复历史。
- 文件名使用可移植字符和稳定领域名，例如 modules/audio/preview.md、tasks/audio.md。
- 路径默认相对项目根；Markdown 链接相对当前文档。链接标签可以中文，目标文件名尽量无空格/括号。
- 每个 task/command/pitfall 使用一个二级标题；其内部内容用三级标题或字段列表，方便按标题读取。
- 外部既有设计书可以直接链接。路径只在某环境有效时注明环境和替代查找入口。

## 模板去向

| 模板 | 目标位置 | 何时新增/更新 |
|---|---|---|
| README.md | 交接根/README.md | 初始化、资料映射/入口变化 |
| PROJECT.md | 交接根/PROJECT.md | 初始化、全局架构/主要领域变化 |
| CURRENT.md | 交接根/CURRENT.md | 每次有效交接或检查点 |
| ROUTES.md | 交接根/ROUTES.md | 路由缺失、模块新增/迁移 |
| MODULE.md | modules/<domain>/<module>.md | 对该模块有新事实/行为变化 |
| TASK.md | tasks/<domain>.md 中一个条目 | 用户确认目标、任务进度/验收变化 |
| COMMAND.md | commands/<environment-or-domain>.md 中一个条目 | 可复用命令及条件得到明确 |
| PITFALL.md | pitfalls/<environment-or-domain>.md 中一个条目 | 失败值得复用、复核或出现替代方案 |
| DECISION.md | decisions/<id>.md | 长期决策及其依据明确 |
| SESSION.md | sessions/<id>.md | 本次工作有可交接的信息 |

## 更新与状态判定

1. 模块：更新当前行为，引用 session/决策解释变化；不把每次历史都追加到卡片。
2. 任务：验收逐条记录满足/未满足/unknown；仅全部满足才为 done。无需运行测试的任务可用实际审核/检查证据验收。
3. 阻塞：写无法继续的具体原因、解除条件、能独立推进的部分；不能只写“待处理”。
4. 取消：记录用户决定/需求变更的来源；不能因 agent 没做就改为 cancelled。
5. 命令：工作目录、shell、工具版本、前置条件、命令、预期结果、实际结果缺一时补 unknown；未执行写 unknown/observed。
6. 坑：失败症状是 observed，根因可以 inferred；若各结论置信度不同，在正文分别标注，不合并为笼统 verified。
7. 已解决的坑仍可 active，表示它仍适用于相应环境；superseded 表示被新规则取代。
8. 决策：保留为什么这样做、影响、替代方案和来源；不虚构讨论过的替代方案。
9. Session：已完成/仅编辑/仅探索/仅计划分开记录；引用当前任务卡片，不重新维护一份任务状态真相。
10. CURRENT：下一步包含入口、最小动作、成功标准、必要条件；并注明这只是旧目标的建议，接手应以新要求为准。

## 去重与拆分

先按领域、关键词和 ID 搜索，再创建条目。同问题的新验证补到既有命令/坑；环境不同则分条或明确区分环境。
不要把相同命令全文写在命令、坑、CURRENT、session 四处；命令是主记录，其他资料引用其 ID 和位置。
已完成任务积累较多时移到 tasks/archive/<domain>-<period>.md，保留原 ID，更新链接；活动任务不归档。
卡片拆分时旧路径保留短迁移指针或更新所有受管链接，避免留下无提示的断链。

## 常见错误与正确写法

| 错误 | 正确做法 |
|---|---|
| “已完成”，但只写代码没验证 | in_progress；列验收缺口和下一步 |
| “测试通过”，实际仅程序退出码 0 | 记录具体检查结果及证明范围 |
| “原因是权限问题”，仅看到 Permission denied | 症状 observed；具体根因 unknown/inferred |
| 写一个据说能用的命令并标 verified | 标 unknown/inferred；写验证入口 |
| CURRENT 保存 complete，所以项目已探索完整 | 保存状态 complete；模块覆盖仍 partial |
| 干净工作区意味着本次没有改代码 | 检查已知基线后的提交；基线未知则明确未知 |
| 未写阻塞意味着没有阻塞 | 写“本次检查范围内未发现”或 unknown |
| 把前任所有 todo 作为本轮要求 | 先匹配用户本轮目标，其他任务只作导航 |
| 为缩短文档删掉长期待办 | 摘要保留 ID，详细记录按领域/归档可检索 |
| 保存日志 URL 当作全部证据 | 保留关键结果摘要，注明 URL 可访问性 |
