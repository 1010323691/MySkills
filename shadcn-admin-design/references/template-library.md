# 内置风格模板

在需求访谈进入风格选择时，先打开 [模板展示页](../assets/templates/gallery.html)，让用户比较完整页面与组件，而不是只看风格名称。每组均为本技能自带的离线 HTML/CSS/JS 设计原型，不是上游源码副本，也不是已接入后端的生产项目。

## 可选方向

| 编号 / ID | 名称与主色 | 布局与密度 | 适用场景 |
|---|---|---|---|
| 01 / business-blue | 商务蓝 · #2563EB | 侧栏、中等留白、清晰边框 | 订单、CRM、企业 SaaS |
| 02 / minimal-neutral | 极简黑白 · #18181B | 顶部导航、低装饰、紧凑圆角 | 内容管理、内部工具、开发者控制台 |
| 03 / soft-sage | 柔和青绿 · #0F766E | 侧栏、宽松、大圆角与柔和卡片 | 协作、客户服务、人事 |
| 04 / warm-editorial | 暖色编辑风 · #A54A21 | 顶部导航、衬线标题、暖白背景 | 品牌运营、电商、工作室 |
| 05 / dark-ops | 深色监控 · #8BB7FF | 侧栏、深色表面、鲜明数据 | 运维、实时运营、分析 |
| 06 / compact-indigo | 紧凑靛蓝 · #4F46E5 | 窄侧栏、高密度、紧凑控件 | ERP、仓储、财务 |

主题数据和 tokens 的事实源是 [catalog.json](../assets/templates/catalog.json)。本表帮助初选，具体颜色、布局和密度仍可按需求调整。不要把某组场景当成其他风格不适用的限制。

## 每组提供五个视图

每组入口为 `assets/templates/<ID>/index.html`。用 URL hash 直接打开指定视图：

- `#overview`：指标卡、面积趋势、分组柱状图、渠道环形图、最近订单与目标进度。
- `#orders`：搜索、状态筛选、金额排序、分页、跨页勾选、CSV 导出、详情抽屉与新建入口演示。
- `#charts`：折线图、柱状图、面积图、环形图，刻度、图例和数值说明。
- `#components`：按钮尺寸和状态、图标按钮、开关、复选、单选、下拉、日期、数字、文本域、单值 / 双值 / 步进滑块、滚动区域与滚动条、横向卡片滑动、鼠标与键盘可调分栏、标签、头像和进度。
- 同一组件视图的「反馈与容器」页签：弹窗、抽屉、Toast、下拉操作、Tooltip、Alert、空状态、骨架屏、折叠面板、卡片与面包屑。
- `#settings`：原生表单校验、通知开关、保存 / 恢复默认；保存仅写浏览器本地存储。

折线与柱状图点位有原生 title 提示，图表也有可读说明；这是静态图表原型，生产接入与高级图表交互需另行实现。新建入口不提交订单，删除 / 归档不会改业务数据，避免把演示动作描述为已完成真实业务功能。

## 如何向用户展示与选用

1. 打开展示页；按用户已知场景推荐 2–3 组比较，但完整目录保持可查看。
2. 用 `previews/<ID>.png` 展示仪表盘，用 `<ID>-components.png` 查看细节，用 `<ID>-mobile.png` 查看手机布局。图片必须用绝对路径直接展示。
3. 需要更清楚交互时打开对应 HTML 视图；原型可直接以 `file://` 打开，无需服务器、npm install 或外网。
4. 用户可点击「选择这组风格」并复制说明到对话。页面的本地选中状态不是来自用户对话的实施批准，也不应被代理自行当成授权。
5. 将明确选择的 ID、颜色、布局与后续调整记录进简报，继续问业务和技术约束。用户有品牌色时优先品牌色；可混合局部模式，但需展示混合后的具体方案。
6. 模板截图是风格参考，不能直接冒充本次业务效果图。按实际页面、字段、关键流程制作新版本预览，用户明确确认后才实施。

## 映射到 shadcn-admin

| 原型模块 | 实施参考 |
|---|---|
| 框架与导航 | Sidebar、Header、Main、Breadcrumb、Tabs |
| 列表 | Table + TanStack Table、DataTableToolbar、分页与 URL 状态 |
| 图表 | Recharts LineChart / BarChart / AreaChart / PieChart |
| 按钮与输入 | Button、Input、Textarea、Select、Checkbox、RadioGroup、Switch、Calendar |
| 滑块与滚动 | Slider、ScrollArea、Carousel、Resizable |
| 弹层与反馈 | Dialog、AlertDialog、Sheet、DropdownMenu、Tooltip、Sonner、Alert、Skeleton |
| 信息容器 | Card、Badge、Avatar、Progress、Separator、Accordion |

此表表达设计映射，不保证上游已有每个组件。实现前检查目标项目是否安装、版本是否兼容、上游是否定制，按批准范围适配。不要把原型 DOM 直接包装成 React 后声称完成 shadcn 集成。

## 维护与打包

保留整个 `assets/templates/`，每组依赖同级 `shared/`。只复制某个 `index.html` 会缺少样式与脚本。不需要外部字体或图片，SVG 图标与图表由本技能绘制。

- 修改 `catalog.json` 后运行 `python scripts/build_templates.py`，生成六个入口和浏览器元数据。
- 共享布局与组件在 `shared/base.css`、`shared/dashboard.js`；目录展示在 `gallery.html`、`shared/gallery.css`、`shared/gallery.js`。
- 使用已有 Playwright 环境运行 `node scripts/render_templates.cjs` 重新截图并检查视图边界。找不到默认 Chromium 时可用环境变量 `ADMIN_BROWSER_EXECUTABLE` 指向已安装浏览器；`NODE_PATH` 可指向已有依赖目录。
- 运行 `node scripts/check_templates.cjs` 检查有意义的交互行为。截图后实际查看变更涉及的主题与视图。
- 修改技能自带模板不需要走目标项目的设计确认门槛；若应用到用户项目，仍须遵守 SKILL.md 的确认流程。
