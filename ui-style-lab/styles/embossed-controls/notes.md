# 浮雕灰 · 按钮与搜索栏

基于用户提供的滑块图片和已完成的 [浮雕橙开关](../embossed-orange-switch/demo.html) 延展设计。原图保存在 [关闭参考](../embossed-orange-switch/reference-off.jpg)、[开启参考](../embossed-orange-switch/reference-on.jpg)。本组是同风格原创组件，不是参考图中已出现元素的直接还原。

## 设计

- 银灰按钮：金属感圆边、浅浮雕纹理及右下柔和投影。
- 橙色主按钮：延续滑块的开启色，用于强调主要操作。
- 圆形图标按钮：保留滑块的圆形轮廓与中心纹理。
- 搜索栏：胶囊形内凹槽，浮起的圆形提交按钮，支持清空。
- 按钮默认高 `56px`；搜索栏高 `74px`；纹理间距 `4px`。
- 悬停、按压、焦点、禁用和切换状态是为新组件补充的设计。

## 引入

```html
<link rel="stylesheet" href="路径/component.css">
<script src="路径/component.js" defer></script>
```

普通按钮的外观只依赖 CSS。交互脚本每个页面引入一次；`demo.js` 是展示页的本地搜索示例，不需要复制到业务项目。

```html
<button type="button" class="usl-metal-button usl-metal-button--textured">收藏</button>
<button type="button" class="usl-metal-button usl-metal-button--orange">继续</button>
<button type="button" class="usl-metal-button" disabled>暂不可用</button>
```

图标按钮添加 `usl-metal-button--round`，内放 SVG 并提供 `aria-label`。需要可保持的按压状态时，加 `data-usl-toggle` 和 `aria-pressed="false"`；脚本自动切换并派发 `usl-button-toggle`，事件中的 `detail.pressed` 表示当前状态。

## 搜索栏

```html
<form class="usl-metal-search" role="search" aria-label="站内搜索">
  <input class="usl-metal-search__input" type="search" name="q"
         aria-label="搜索关键词" placeholder="搜索…">
  <button class="usl-metal-search__clear" type="button" aria-label="清空搜索" hidden>×</button>
  <button class="usl-metal-button usl-metal-button--round usl-metal-search__submit"
          type="submit" aria-label="提交搜索">→</button>
</form>
```

输入后显示清空按钮，点击清空会恢复输入焦点。点击提交或按 Enter 发出 `usl-search` 事件，不刷新页面、不发送网络请求。业务项目监听事件接入自己的搜索逻辑：

```js
document.addEventListener('usl-search', (event) => {
  const query = event.detail.query;
  // 在这里接入搜索；query 已去除首尾空白，可为空字符串。
});
```

搜索栏可省略前置图标或清空按钮。禁用时给输入、清空和提交按钮分别加 `disabled`，表单加 `usl-metal-search--disabled` 显示对应外观。原生输入支持键盘操作，容器提供 `focus-within` 焦点环。

可覆盖组件变量 `--usl-metal-accent`（橙色）、`--usl-metal-radius`（圆角）和 `--usl-metal-font`（字体）。通过组件类设置高度或内边距；组件 CSS 不修改宿主页面全局样式，不使用在线字体、图片或第三方库。
