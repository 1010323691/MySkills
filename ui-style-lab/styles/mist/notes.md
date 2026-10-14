# 雾灰 · Mist 新拟态组件库

## 独立管理

本套件名称为 **雾灰 · Mist**，唯一标识 `mist`，当前版本 `1.3.0`。全部源代码、原图、展示页和说明集中在 `ui-style-lab/styles/mist/`，身份信息与入口清单见 [style.json](style.json)。

以后用户说“雾灰”“Mist”或“这一套新拟态样式”时，修改本目录，保持名称和标识稳定。颜色、圆角、阴影和字体统一在 `tokens.css` 管理；组件外观在 `component.css`，交互在 `component.js`。展示页布局及模拟数据放在 `demo.css` / `demo.js`，不混入可复用组件代码。

新增组件时同时维护使用说明、独立展示页与 `style.json` 的组件清单；按实际发布变更更新版本，并保持总展示页中的版本一致。更换另一套视觉风格时建立其他套件，不覆写 Mist。相邻样式不引入本套件文件，本套件也不依赖相邻样式；完整复制此目录即可独立保留或复用。

CSS 使用 `.mist` 根容器、`.mist-` 类名前缀、`--mist-` 变量前缀，交互事件使用 `mist-` 前缀，避免与其他样式混用。仓库与 skill 为同一目录时保存一次；安装副本不在仓库中时，按 skill 的完整同步流程更新两处。

参考图：[reference.jpg](reference.jpg)，用户上传的 NEUMORPHISM 智能家居面板。已原样保存。本套保留参考图的柔和双向阴影，默认材质现为米白浮雕版本，恢复参考图更明显的同色凸起感。

## 文件与分工

- `style.json`：套件名称、唯一标识、版本、入口与文件清单。
- `tokens.css`：本套件独立的颜色、阴影、圆角与字体参数。
- `component.css`：可复用组件外观，不修改宿主页面全局样式。
- `component.js`：开关、场景选择、按钮选择、分段控制和温控旋钮；每个页面引入一次，在组件 HTML 渲染后加载。
- `demo.html` + `demo.css` + `demo.js`：完整展示页、参考图布局、设备搜索、弹窗与本地演示数据。
- `examples.html`：可直接打开的最小使用示例。

## 材质参数

| 参数 | 默认值 |
| --- | --- |
| 画布 / 表面 | `--mist-canvas: #e9e4da` / `--mist-surface: #e9e4da` |
| 浮起表面 | `--mist-raised-fill: var(--mist-surface)`，与画布同色 |
| 主文字 / 次级文字 | `#303033` / `#65656a` |
| 卡片阴影 | 右下 `10px 10px 22px #c8c2b6` / 左上 `-10px -10px 22px #fffdf7` |
| 小组件阴影 | `5px` 位移，`10px` 模糊，含暖白高光 |
| 内凹阴影 | 两个方向的 `inset 5px / 10px` 阴影 |
| 卡片圆角 | `42px` |

没有增加金属光圈、点阵纹理或橙色装饰。用同色表面、留白、弧线和阴影表达层次。

## 组件清单

| 组件 | 类名 / 标记 | 交互 |
| --- | --- | --- |
| 容器与设计变量 | `.mist` | 组件所在的父容器 |
| 浮起卡片 | `.mist-card` | 内容容器 |
| 胶囊按钮 | `.mist-button` | 原生 button，支持 disabled |
| 内凹 / 深色按钮 | `--inset` / `--dark` 后缀类 | 按压 / 主操作变体 |
| 圆形图标按钮 | `.mist-icon-button` | SVG 图标 + aria-label |
| 开关 | `.mist-switch` | role=switch，aria-checked |
| 温控旋钮 | `.mist-dial[data-mist-dial]` | 弧线拖动、方向键、Home / End、PageUp / PageDown |
| 场景卡片 | `.mist-scene[data-scene]` | aria-pressed 状态选择 |
| 设备列表行 | `.mist-device` | 原生按钮，演示打开设备详情 |
| 头像 | `.mist-avatar` | 可替换内部 SVG 为业务头像 |
| 状态徽标 | `.mist-chip` | 凹入的小标签 |
| 输入框 | `.mist-field` / `.mist-input` | 真实文本输入 |
| 搜索栏 | `.mist-search` / `__input` | 原生 form，业务侧监听 submit |
| 分段选择 | `.mist-segments` / `__segment` | 单选，使用 aria-pressed |
| 复选框 / 单选框 | `.mist-choice` | 原生 checkbox / radio |
| 连续滑杆 | `.mist-range` | 原生 range |
| 进度条 | `.mist-progress` | role=progressbar，显式更新 aria-valuenow |
| 弹出菜单 | `.mist-menu` | hidden 属性控制，配 aria-expanded |
| 弹窗 | `.mist-dialog` | 原生 dialog，showModal / close，Esc 关闭 |

类名均带 `mist-` 前缀；温控 SVG 和卡片的完整结构可从 `demo.html` 复制，简单组件可参考 `examples.html`。

## 最小用法

```html
<link rel="stylesheet" href="路径/tokens.css">
<link rel="stylesheet" href="路径/component.css">
<script src="路径/component.js" defer></script>
<div class="mist" style="background: var(--mist-canvas); padding: 32px">
  <button class="mist-button" type="button">按钮</button>
  <button class="mist-button" type="button"
          aria-pressed="false" data-toggle>可保持的按压状态</button>
  <label class="mist-field">房间名称
    <input class="mist-input" type="text" placeholder="输入名称">
  </label>
</div>
```

父容器必须有 `.mist`，展示背景使用 `--mist-canvas`；表面使用同色的 `--mist-surface` 与 `--mist-raised-fill`。可在父容器覆盖 `--mist-canvas`、`--mist-raised-fill`、`--mist-surface`、`--mist-ink`、`--mist-muted`、`--mist-shadow`、`--mist-small-shadow`、`--mist-inset` 和 `--mist-radius`；换颜色时同步调整背景和阴影，保持表面与画布同色，并给高光和暗影留出足够明度差。

## 事件与业务接入

`component.js` 只处理基础组件状态，不操作真实设备。监听冒泡事件：

```js
document.addEventListener('mist-toggle', event => {
  console.log(event.target, event.detail.checked);
});
document.addEventListener('mist-temperature-change', event => {
  console.log(event.detail.value);
});
document.addEventListener('mist-segment-change', event => {
  console.log(event.detail.value);
});
```

任意原生按钮都支持点击与键盘操作；可保持的按钮加 `data-toggle` 和 `aria-pressed`。开关用 `aria-checked`，并提供稳定的可访问名称。分段按钮的值取 `data-period`，未提供时取按钮文字。

搜索栏本身不预设接口。`demo.js` 示例按输入值筛选四个设备，支持中英文及清空。设备详情中的电源状态在本次页面会话中保持；新建场景会更新计数和 See All 列表；刷新恢复初始演示。账户菜单仅提供演示反馈。

进度条填充使用 `--mist-progress`，更新数值时同步修改 `aria-valuenow`。弹窗包含真实表单和取消按钮，使用原生 dialog 管理模态焦点与 Esc。

## 参考还原与补充设计

上方还原参考图的温控卡片、早晨 / 夜间场景、场景汇总条、头像与问候卡、用电面板和四条设备列表。下方按钮、输入框、搜索栏、选择控件、进度条、滑杆和弹窗是同风格补充组件。

字体、阴影与尺寸根据图片近似；头像使用原创几何山峰 SVG；温控采用可操作的 `16–28°C` 示例范围，方便实际演示，非原截图刻度的精确复刻。所有图标、弧线和阴影都由 HTML / SVG / CSS 实现，不以参考截图冒充组件。

## Narrify 后台适配（2026-10-13）

[narrify-admin.html](narrify-admin.html) 为 Narrify Vue 管理总览的离线静态预览，数据来自隔离布局样本，可切换浅色 / 深色。导航和业务按钮仅展示外观，真实操作在 Narrify 应用内执行；原组件库 demo 保留真实交互。

[narrify-admin.css](narrify-admin.css) 是后台材质适配层，引用本目录 tokens.css，根容器使用 `class="mist admin-shell"`，配合 Narrify 的 admin.css 布局和原 Vue 组件使用。覆盖导航、账户菜单、指标与图表卡片、表格、分页、搜索、表单、选择控件、开关、标签、进度条、加载态、空态、抽屉、确认弹窗、通知与音乐库。按钮标记为 `data-ui-button`；样式只作用于 Mist 后台容器。

当前浅色使用米白浮雕表面和双向阴影；后台数据密度较高，卡片采用 28px（窄屏 22px）圆角。深色参数是本次补充设计。保留原语义图表和告警配色；提供 hover / active / focus-visible / disabled 状态并遵循 reduced-motion。

应用入口：AdminLayout.vue 导入 admin.css 和 admin-mist.css；应用通知与确认弹窗同步使用 `.mist.admin-shell.admin-feedback`。无需数据库迁移或新增运行配置。验证通过类型检查、生产构建、后台 29 项回归，以及 1440px / 390px 的九个页面布局检查。

### 第二轮覆盖审计

补齐音乐试听播放按钮与进度槽、曲目编辑标签、所有 WorkbenchStatus 状态标签、Alert 提示面板与通知操作按钮，以及管理员登录页（用户登录页继续使用原样式）。音乐库旧文件夹卡片位于 `v-if="false"` 分支，不是当前可见界面，因此没有为其保留无效适配。

新增 Narrify 的 `scripts/test-admin-mist-browser.mjs`：使用隔离接口样本验证九个页面、六个配置分区、有数据的解析报告、五个章节详情标签、音乐视图导航 / 标签编辑 / 播放控件、状态标签、输入确认弹窗、通知、管理员登录，以及按压 / 键盘焦点 / 禁用 / 加载 / 错误 / 深色状态。1440px 和 390px 均通过，不向真实后端提交变更。

### 早期白色页面背景（已由 v1.2.0 默认材质取代）

按用户要求，Narrify 适配层的浅色页面、侧栏与管理员登录背景改为 `#ffffff`，组件继续使用 Mist 的 `#d9d9dc` 材质与阴影。页面背景由 `--background` 管理，组件表面由 `--mist-surface` 管理；深色模式保留原深灰背景。基础 Mist 套件 tokens 和智能家居示例不受此业务适配影响。浏览器审计新增白色页面、侧栏、登录背景断言。

### 早期白色组件材质（已由 v1.2.0 默认材质取代）

用户进一步确认，Narrify 的组件本身也应以白色为主。适配层现覆盖 `--mist-surface: #ffffff`，卡片、输入框、普通与主操作按钮、侧栏控件、抽屉及弹窗统一使用白色表面。以偏冷的低对比投影、白色高光及内凹阴影表现浮起 / 嵌入的模块感；同步调整 card / muted / accent / input 等宿主变量与窄屏阴影，避免旧灰色残留。危险操作与图表继续使用语义颜色。深色模式保持原材质参数。该业务适配不改写基础 Mist 的原参考套件。

## 白色材质的悬浮层次（v1.1.4）

参考 [用户当前白色后台截图](reference-white-admin.png)，已保存在本套件中。[白色效果对照页](white-material.html) 可并排比较原纯白与调整后的雾白材质，并操作按钮和搜索框；[完整后台预览](narrify-admin.html) 引用更新后的适配 CSS。v1.2.0 已将雾白悬浮参数设为 tokens.css 中的组件库默认值；后台参数在 narrify-admin.css 中适配。

画布由纯白改为接近白色的 `hsl(216 22% 95.5%)`（约 #f1f3f6），组件表面为 #f8fafc，高光为 #fff。大卡片使用很轻的 145° 表面渐变、右下柔影、左上高光与浅接触阴影；按钮使用更短的凸起阴影，按下时切换为内凹，输入槽保持 inset。卡片间保持 24px 空隙与滚动区域留白。窄屏缩短阴影，深色材质继续使用原参数。

纯白画布上的纯白高光无法形成明度差；仅增大右下阴影通常会变成普通投影卡片。这里用少量明度差保持白色观感，让双向光影重新可见。此修改保存于组件库适配层和静态示例，未修改或部署 Narrify 业务仓库；接入实际后台时同步其 admin-mist.css 对应参数。

## v1.2.0：主组件库默认采用雾白悬浮

用户要求将新的白色悬浮效果应用到 Mist 主库，现已更新 tokens.css、component.css、demo.css、完整展示页、最小示例、总展示页及预览截图。主入口仍为 demo.html，名称与标识保持雾灰 · Mist / mist。卡片、场景、列表、按钮、开关滑块和分段选择都使用统一设计变量，避免硬编码旧灰色阴影；输入框、搜索栏和按压状态保持内凹反馈。

原先展示页“按下”按钮同时带固定 --inset 类和可切换 aria-pressed，导致再次点击仍然内凹；现仅由 aria-pressed 表达可切换状态。--inset 类仍可用于明确需要固定内凹的变体。

## 当前默认：米白浮雕（v1.3.0）

用户选择米白主色调，并希望恢复最初灰色参考的突出模块感。画布与组件表面统一为 #e9e4da，暖白高光 #fffdf7、暗影 #c8c2b6；去除上一版白色卡片渐变，恢复 10px / 22px 的双向阴影。小按钮为 5px / 10px，按压和输入槽使用成对 inset 阴影。图标槽、温控刻度与次级文字同步改为暖中性色。

主展示页、最小示例、总展示页和 Narrify 静态适配层统一采用本色调；旧白色对照页显式保留自己的参数，供比较。套件仍为雾灰 · Mist，标识 mist 稳定。交互和业务接入方式沿用原库，本次只更新样式与静态展示，不修改外部业务项目。
