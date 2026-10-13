# 雾灰 · Mist 新拟态组件库

## 独立管理

本套件名称为 **雾灰 · Mist**，唯一标识 `mist`，当前版本 `1.0.0`。全部源代码、原图、展示页和说明集中在 `ui-style-lab/styles/mist/`，身份信息与入口清单见 [style.json](style.json)。

以后用户说“雾灰”“Mist”或“这一套新拟态样式”时，修改本目录，保持名称和标识稳定。颜色、圆角、阴影和字体统一在 `tokens.css` 管理；组件外观在 `component.css`，交互在 `component.js`。展示页布局及模拟数据放在 `demo.css` / `demo.js`，不混入可复用组件代码。

新增组件时同时维护使用说明、独立展示页与 `style.json` 的组件清单；按实际发布变更更新版本，并保持总展示页中的版本一致。更换另一套视觉风格时建立其他套件，不覆写 Mist。相邻样式不引入本套件文件，本套件也不依赖相邻样式；完整复制此目录即可独立保留或复用。

CSS 使用 `.mist` 根容器、`.mist-` 类名前缀、`--mist-` 变量前缀，交互事件使用 `mist-` 前缀，避免与其他样式混用。仓库与 skill 为同一目录时保存一次；安装副本不在仓库中时，按 skill 的完整同步流程更新两处。

参考图：[reference.jpg](reference.jpg)，用户上传的 NEUMORPHISM 智能家居面板。已原样保存。本套采用同色浅灰材质和柔和双向阴影，替代上一版金属纹理方向。

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
| 表面 | `#d9d9dc`，与展示页背景一致 |
| 主文字 / 次级文字 | `#303033` / `#65656a` |
| 卡片双向阴影 | 右下 `10px 10px 22px #b9b9bd`，左上 `-10px -10px 22px #f8f8fa` |
| 小组件阴影 | `5px` 位移，`10px` 模糊 |
| 内凹阴影 | 两个方向的 `inset 5px` 阴影 |
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
<div class="mist" style="background: #d9d9dc; padding: 32px">
  <button class="mist-button" type="button">按钮</button>
  <button class="mist-button" type="button"
          aria-pressed="false" data-toggle>可保持的按压状态</button>
  <label class="mist-field">房间名称
    <input class="mist-input" type="text" placeholder="输入名称">
  </label>
</div>
```

父容器必须有 `.mist`，且展示背景应与 `--mist-surface` 一致。可在父容器覆盖 `--mist-surface`、`--mist-ink`、`--mist-muted`、`--mist-shadow`、`--mist-small-shadow`、`--mist-inset` 和 `--mist-radius`；换颜色时同步调整背景和阴影，保持同色材质。

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
