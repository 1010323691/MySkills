# 后台图表与仪表盘 · Admin Atlas

标识 `admin-light` · v2.0.0。沿用原套件目录，重做为可独立选择的图表样式目录，不再把所有参考统一换色。

入口 [demo.html](demo.html) · 样式 [charts.css](charts.css) · 结构化清单 [patterns.json](patterns.json)。前版工作台保留为 [workspace.html](workspace.html)，其 component.css / component.js / demo.css 为前版专用。

## 复用方式

每一种图表均有独立 HTML 文件，内嵌真实 SVG（不使用截图背景），复制其中 `.usl-chart-card` 区块、引用 `charts.css`，放在 `.usl-charts` 容器里即可。仪表盘文件提供独立布局与图表组合，可复制 `.usl-chart-layout`，引入 charts.css 与 catalog.css。图表不依赖 JS，目录筛选使用 catalog.js，不使用 fetch 或 CDN。

```html
<link rel="stylesheet" href="charts.css">
<section class="usl-charts">
  <!-- 将 charts/sales-area.html 内的 article 复制到此处 -->
</section>
```

每种图表的 SVG 几何、图例、数据点及 aria-label 均在对应独立 HTML 内；修改数据时需要同步更新坐标 / 柱高 / 弧长 / 标签。本版本是可复制的静态样式，不提供自动数据渲染 API。`.usl-chart-point` 提供鼠标 hover、键盘 focus 和原生 title 提示（键盘可读取 aria-label），这些状态为补充设计。

## 提取范围与近似项

五张原图已保存为 reference-1.jpg 至 reference-5.jpg；目录底部提供原图对照。20 项覆盖图片中可辨识的主要图表与数据可视化类型；10 项分别对应五张拼图中的上下两个仪表盘。相似图表也按参考形态分开：紫绿面积、淡紫折线、绿色节点线；条纹目标柱、堆叠现金流、橙色渐变柱、蓝色高亮柱、紫绿分组柱等。地图、日程、进度卡也分别收录。

原图分辨率较低，无法辨认精确字体、数值与全部图例。参考来源指视觉形态，不声称获得原始源码。图表值、阈值、时间、地理底图、车辆 SVG、文案均为近似演示。卡片尺寸根据可读性调整。参考的细微线条与阴影由原生 SVG/CSS 重建；表格与人物 / 房屋照片不是本次图表提取重点。仪表盘保存的是视觉布局骨架与代表图表组合，非完整业务系统或像素级截图复刻。

## 图表选型索引

| 样式 | 适用场景 | 参考 |
| --- | --- | --- |
| [青蓝多层弧环](charts/ranking-arcs.html) | 门店 / 客户的目标达成对比 | 图 1 · 上方左侧 Customer Ranking |
| [横向圆角漏斗](charts/stage-funnel.html) | 访问→询价→确认→开票→交付的销售转化 | 图 1 · 上方右侧 Customer Ranking |
| [紫绿双层进度环](charts/product-rings.html) | 两条产品线各自的销量目标完成率 | 图 1 · 下方 Product Sales Statics |
| [紫绿柔光双面积](charts/sales-area.html) | 产品收入、销售量等连续趋势对比 | 图 1 · 下方 Sales Summary |
| [薄荷条纹目标柱](charts/engagement-bars.html) | 月度活跃、客户参与率与容量目标比较 | 图 2 · 上方 Client Engagement Over Time |
| [绿色分段径向仪表](charts/distribution-ticks.html) | 机会覆盖、任务完成、设备利用等单项比例 | 图 2 · 上方 Client Distribution |
| [深绿青柠现金流柱](charts/cashflow-stack.html) | 已到账 / 待到账，已确认 / 待确认的每月组成 | 图 2 · 下方 Cashflow |
| [藏蓝财务占比环](charts/expense-donut.html) | 房租、投资、订阅等支出构成 | 图 2 · 下方 Statistic |
| [珊瑚渐变年度柱](charts/annual-bars.html) | 月销售量、房源成交量、线索数量 | 图 3 · 上方 Annual Performance |
| [多色横向构成条](charts/listing-share.html) | 房源类型、订单渠道或商品类型的份额 | 图 3 · 上方 Total Listings |
| [钴蓝重点周柱](charts/worktime-bars.html) | 工时、运动时长、产能的周内比较 | 图 3 · 下方 Progress |
| [彩色泳道日程](charts/meeting-timeline.html) | 团队会议、成员排期、项目资源占用 | 图 3 · 下方 Meeting Scheduling |
| [淡紫柔角折线](charts/work-progress-line.html) | 项目吞吐、工作进度、完成量与计划比较 | 图 4 · 上方 Work Progress Overview |
| [彩虹半环评分仪表](charts/credit-gauge.html) | 健康评分、服务质量、设备性能与信用分展示 | 图 4 · 上方 Credit Score |
| [迷你趋势指标卡](charts/kpi-sparkline.html) | 顶部 KPI 同时显示总值与近期方向 | 图 4 · 上方 Projects / Clients / Revenue |
| [荧光绿紫分组柱](charts/weekly-grouped.html) | 每周收入 / 支出、当前 / 前期数值比较 | 图 4 · 下方 Weekly statistics |
| [紫绿细线目标条](charts/goal-progress.html) | 预算目标、储蓄目标、项目交付进度 | 图 4 · 下方 Financial goals；图 2 · 下方 Saving Plans |
| [绿色节点双折线](charts/delivery-lines.html) | 物流配送：已交付 / 延误随小时变化的运营比较 | 图 5 · 上方 Delivery performance |
| [浅色地图状态点](charts/fleet-map.html) | 车队位置、配送分布、资产运行状态 | 图 5 · 上方 Live Tracking Fleet |
| [装载卡片进度条](charts/loading-progress.html) | 仓储装载、运输准备、批次处理完成率 | 图 5 · 下方 Trucks currently in warehouse |

<a id="ranking-arcs"></a>
## 青蓝多层弧环

- 文件：[charts/ranking-arcs.html](charts/ranking-arcs.html)
- 类型：仪表与环形；来源：图 1 · 上方左侧 Customer Ranking。
- 适用场景：门店 / 客户的目标达成对比。
- 数据要求：各对象独立的达成率，范围 0–100%；每条弧对应一个对象。
- 使用边界：各环不是总量组成，不应相加。
- 配色标识：`cyan`；形态与颜色独立于其他图表。

<a id="stage-funnel"></a>
## 横向圆角漏斗

- 文件：[charts/stage-funnel.html](charts/stage-funnel.html)
- 类型：结构与转化；来源：图 1 · 上方右侧 Customer Ranking。
- 适用场景：访问→询价→确认→开票→交付的销售转化。
- 数据要求：按业务顺序提供递减的阶段人数及转化率。
- 使用边界：适合顺序流失；非递减流程改用流程图。
- 配色标识：`cyan`；形态与颜色独立于其他图表。

<a id="product-rings"></a>
## 紫绿双层进度环

- 文件：[charts/product-rings.html](charts/product-rings.html)
- 类型：仪表与环形；来源：图 1 · 下方 Product Sales Statics。
- 适用场景：两条产品线各自的销量目标完成率。
- 数据要求：两组当前值 / 目标值，分别映射 0–100%。
- 使用边界：不是饼图；两个进度值无需相加到 100%。
- 配色标识：`mint`；形态与颜色独立于其他图表。

<a id="sales-area"></a>
## 紫绿柔光双面积

- 文件：[charts/sales-area.html](charts/sales-area.html)
- 类型：趋势与折线；来源：图 1 · 下方 Sales Summary。
- 适用场景：产品收入、销售量等连续趋势对比。
- 数据要求：同一时间轴、同一单位的两条系列。
- 使用边界：面积重叠不代表累计；不把插值曲线当作额外观测。
- 配色标识：`mint`；形态与颜色独立于其他图表。

<a id="engagement-bars"></a>
## 薄荷条纹目标柱

- 文件：[charts/engagement-bars.html](charts/engagement-bars.html)
- 类型：柱状与比较；来源：图 2 · 上方 Client Engagement Over Time。
- 适用场景：月度活跃、客户参与率与容量目标比较。
- 数据要求：当前值 + 统一目标值；月份等时间标签。
- 使用边界：背景条纹表示目标容量，需明确标注。
- 配色标识：`emerald`；形态与颜色独立于其他图表。

<a id="distribution-ticks"></a>
## 绿色分段径向仪表

- 文件：[charts/distribution-ticks.html](charts/distribution-ticks.html)
- 类型：仪表与环形；来源：图 2 · 上方 Client Distribution。
- 适用场景：机会覆盖、任务完成、设备利用等单项比例。
- 数据要求：一个百分比值；亮色段为已完成，灰段为余量。
- 使用边界：展示整体进度，不适合比较多个类别份额。
- 配色标识：`emerald`；形态与颜色独立于其他图表。

<a id="cashflow-stack"></a>
## 深绿青柠现金流柱

- 文件：[charts/cashflow-stack.html](charts/cashflow-stack.html)
- 类型：柱状与比较；来源：图 2 · 下方 Cashflow。
- 适用场景：已到账 / 待到账，已确认 / 待确认的每月组成。
- 数据要求：两段同单位非负值，柱高是合计。
- 使用边界：本实现明确为堆叠组成；收入与支出对比应使用分组柱。
- 配色标识：`lime`；形态与颜色独立于其他图表。

<a id="expense-donut"></a>
## 藏蓝财务占比环

- 文件：[charts/expense-donut.html](charts/expense-donut.html)
- 类型：仪表与环形；来源：图 2 · 下方 Statistic。
- 适用场景：房租、投资、订阅等支出构成。
- 数据要求：分类金额；扇区角度按总金额占比分配。
- 使用边界：少量类别清晰；很小的类别应合并。
- 配色标识：`navy`；形态与颜色独立于其他图表。

<a id="annual-bars"></a>
## 珊瑚渐变年度柱

- 文件：[charts/annual-bars.html](charts/annual-bars.html)
- 类型：柱状与比较；来源：图 3 · 上方 Annual Performance。
- 适用场景：月销售量、房源成交量、线索数量。
- 数据要求：每月非负计数，统一刻度；背景为目标容量。
- 使用边界：柱宽一致，基线从零开始。
- 配色标识：`coral`；形态与颜色独立于其他图表。

<a id="listing-share"></a>
## 多色横向构成条

- 文件：[charts/listing-share.html](charts/listing-share.html)
- 类型：结构与转化；来源：图 3 · 上方 Total Listings。
- 适用场景：房源类型、订单渠道或商品类型的份额。
- 数据要求：多个非负分类数值；总和规范化为 100%。
- 使用边界：长度表示份额；不用于顺序转化。
- 配色标识：`coral`；形态与颜色独立于其他图表。

<a id="worktime-bars"></a>
## 钴蓝重点周柱

- 文件：[charts/worktime-bars.html](charts/worktime-bars.html)
- 类型：柱状与比较；来源：图 3 · 下方 Progress。
- 适用场景：工时、运动时长、产能的周内比较。
- 数据要求：七天时长；高亮当前或选中日。
- 使用边界：突出选中日，不把颜色理解为额外类别。
- 配色标识：`blue`；形态与颜色独立于其他图表。

<a id="meeting-timeline"></a>
## 彩色泳道日程

- 文件：[charts/meeting-timeline.html](charts/meeting-timeline.html)
- 类型：日程与运营；来源：图 3 · 下方 Meeting Scheduling。
- 适用场景：团队会议、成员排期、项目资源占用。
- 数据要求：每条泳道一类任务；提供开始与结束时间。
- 使用边界：时间轴为示例，真实业务需处理重叠与跨日。
- 配色标识：`blue`；形态与颜色独立于其他图表。

<a id="work-progress-line"></a>
## 淡紫柔角折线

- 文件：[charts/work-progress-line.html](charts/work-progress-line.html)
- 类型：趋势与折线；来源：图 4 · 上方 Work Progress Overview。
- 适用场景：项目吞吐、工作进度、完成量与计划比较。
- 数据要求：同一月份的实际 / 计划数列。
- 使用边界：采用折线柔化外观，数据点仍为离散观测。
- 配色标识：`lavender`；形态与颜色独立于其他图表。

<a id="credit-gauge"></a>
## 彩虹半环评分仪表

- 文件：[charts/credit-gauge.html](charts/credit-gauge.html)
- 类型：仪表与环形；来源：图 4 · 上方 Credit Score。
- 适用场景：健康评分、服务质量、设备性能与信用分展示。
- 数据要求：一个有明确最小 / 最大边界的评分。
- 使用边界：色带阈值为演示；业务评分阈值需另行定义。
- 配色标识：`lavender`；形态与颜色独立于其他图表。

<a id="kpi-sparkline"></a>
## 迷你趋势指标卡

- 文件：[charts/kpi-sparkline.html](charts/kpi-sparkline.html)
- 类型：趋势与折线；来源：图 4 · 上方 Projects / Clients / Revenue。
- 适用场景：顶部 KPI 同时显示总值与近期方向。
- 数据要求：摘要值、变化率以及短时间序列。
- 使用边界：迷你图用于方向提示；精确分析使用带刻度图。
- 配色标识：`lavender`；形态与颜色独立于其他图表。

<a id="weekly-grouped"></a>
## 荧光绿紫分组柱

- 文件：[charts/weekly-grouped.html](charts/weekly-grouped.html)
- 类型：柱状与比较；来源：图 4 · 下方 Weekly statistics。
- 适用场景：每周收入 / 支出、当前 / 前期数值比较。
- 数据要求：同单位两组值；每类两个并列柱。
- 使用边界：并列柱适合比较；不要用堆叠掩盖差值。
- 配色标识：`neon`；形态与颜色独立于其他图表。

<a id="goal-progress"></a>
## 紫绿细线目标条

- 文件：[charts/goal-progress.html](charts/goal-progress.html)
- 类型：结构与转化；来源：图 4 · 下方 Financial goals；图 2 · 下方 Saving Plans。
- 适用场景：预算目标、储蓄目标、项目交付进度。
- 数据要求：当前值 / 目标值，标注百分比和数值。
- 使用边界：超过目标时应单独显示超额，不仅截断为 100%。
- 配色标识：`neon`；形态与颜色独立于其他图表。

<a id="delivery-lines"></a>
## 绿色节点双折线

- 文件：[charts/delivery-lines.html](charts/delivery-lines.html)
- 类型：趋势与折线；来源：图 5 · 上方 Delivery performance。
- 适用场景：物流配送：已交付 / 延误随小时变化的运营比较。
- 数据要求：两条同单位序列及小时标签。
- 使用边界：节点代表真实观测；延误值与完成值应分别定义。
- 配色标识：`logistics`；形态与颜色独立于其他图表。

<a id="fleet-map"></a>
## 浅色地图状态点

- 文件：[charts/fleet-map.html](charts/fleet-map.html)
- 类型：日程与运营；来源：图 5 · 上方 Live Tracking Fleet。
- 适用场景：车队位置、配送分布、资产运行状态。
- 数据要求：底图坐标 + 资产标签 + 状态分类。
- 使用边界：当前是原创示意地图，没有真实地理坐标或地图服务。
- 配色标识：`logistics`；形态与颜色独立于其他图表。

<a id="loading-progress"></a>
## 装载卡片进度条

- 文件：[charts/loading-progress.html](charts/loading-progress.html)
- 类型：日程与运营；来源：图 5 · 下方 Trucks currently in warehouse。
- 适用场景：仓储装载、运输准备、批次处理完成率。
- 数据要求：每条资产的编号、进度、状态与目标。
- 使用边界：装饰车辆为本地 SVG 近似，非原图车型。
- 配色标识：`logistics`；形态与颜色独立于其他图表。

## 仪表盘布局与场景

| 仪表盘 | 适用场景 | 布局与组合 |
| --- | --- | --- |
| [蓝青 ERP 销售总览](dashboards/erp-cyan.html) | ERP、财务经营、销售漏斗 | 固定侧栏 + 四项财务 KPI + 弧环排名 / 横向转化漏斗 |
| [薄荷销售分析台](dashboards/sales-mint.html) | 电商、零售、产品销售分析 | 浅色侧栏 + 筛选工具栏 + 经营 KPI + 双进度环 / 双面积趋势 |
| [深绿客户经营台](dashboards/crm-green.html) | CRM、客户参与度、增长机会分析 | 顶部导航 + 主趋势柱 / 径向覆盖仪表 + 客户指标 |
| [青柠藏蓝财务台](dashboards/finance-lime.html) | 个人 / 企业资金管理、收入构成、储蓄计划 | 浅绿侧栏 + 深色账户摘要 + 现金流柱 / 支出环 / 储蓄进度 |
| [珊瑚房产运营台](dashboards/property-coral.html) | 房产 CRM、房源成交、代理人管理 | 浅珊瑚侧栏 + 线索 / 收入 KPI + 年度柱 / 房源分类条 |
| [蓝柠人事工作台](dashboards/hr-blue.html) | 人事协作、会议排期、员工工时 | 顶部导航 + 青柠欢迎指标区 + 日程泳道 / 工时柱 |
| [淡紫项目工作台](dashboards/project-lavender.html) | 项目交付、团队效率、质量评分 | 窄侧栏 + 柔光背景 + 迷你 KPI / 进度折线 / 半环评分 |
| [黑柠财务管理台](dashboards/finance-neon.html) | 财务交易、收支比较、预算目标 | 深色侧栏 + 中性灰内容 + 荧光绿紫分组柱 / 细线目标条 |
| [绿色物流监控台](dashboards/fleet-green.html) | 物流调度、实时车队分布、交付绩效 | 紧凑侧栏 + 运营 KPI + 节点双折线 / 状态地图 |
| [绿色仓储作业台](dashboards/warehouse-green.html) | 仓库作业、装载进度、发运准备 | 紧凑侧栏 + 资源 KPI + 装载资产卡片网格 |

## 验证记录

已在实际浏览器检查分类目录、代表图表、淡紫项目仪表盘和 390px 窄屏布局；窄屏未见卡片横向溢出。验证分类按钮、场景搜索和清空恢复；控制台未见错误。33 个 HTML 的本地资源 / 链接存在，无重复 ID；清单包含 20 个图表与 10 个独立仪表盘预览。两处样式目录按 SHA-256 比较一致。逐项数据点支持 hover / focus 样式及 aria-label，未对每一个数据点逐一鼠标验证。
