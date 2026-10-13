# 浮雕橙 · 立体开关

参考来源：用户上传的两张图片，已原样保存为 [reference-off.jpg](reference-off.jpg) 和 [reference-on.jpg](reference-on.jpg)。只还原中央开关，截图中的字幕、平台水印和鼠标指针不属于组件。

## 还原要点

- 约 `280 × 150px` 的胶囊形凹槽，外缘顶部偏灰、底部明亮。
- 约 `132px` 的圆形滑块，外侧金属感圆环，中心细密浮雕纹理。
- 关闭：滑块在左，灰色槽体，右侧浮雕 O 标记。
- 开启：滑块在右，绿色槽体，左侧浮雕 I 标记。
- 浅灰背景、外侧 OFF / ON 文字、内凹阴影与滑块右下投影。

尺寸、颜色及阴影依据截图估计；中心纹理由重复 CSS 渐变近似，不是原视频的源代码或精确材质。切换动画（360ms）、焦点环、按压和禁用状态为补充设计，静态参考图不能确定原始动画。

## 使用

```html
<link rel="stylesheet" href="路径/component.css">
<script src="路径/component.js" defer></script>

<button class="usl-embossed-switch" type="button"
        role="switch" aria-checked="false" aria-label="电源开关">
  <span class="usl-embossed-switch__well" aria-hidden="true">
    <span class="usl-embossed-switch__mark usl-embossed-switch__mark--on"></span>
    <span class="usl-embossed-switch__mark usl-embossed-switch__mark--off"></span>
  </span>
  <span class="usl-embossed-switch__thumb" aria-hidden="true"></span>
</button>
```

每个页面仅引入一次交互脚本。`aria-checked="true"` 表示开启；添加原生 `disabled` 可禁用。点击、Enter、空格都会切换，状态属性和外观保持同步。纯 CSS 负责外观，脚本只改变属性并派发事件。

```js
document.addEventListener('usl-switch-change', (event) => {
  console.log(event.target, event.detail.checked);
});
```

监听事件后再接入业务逻辑；示例不操作实际设备或服务。直接用代码设置状态时修改 `aria-checked` 属性；它不会自动派发事件。

可以覆盖变量调整宽度（高度及滑块按比例缩放）、状态颜色和动画时长：

```css
.my-switch {
  --usl-switch-width: 224px;
  --usl-switch-off: #737373;
  --usl-switch-green: #22c55e;
  --usl-switch-duration: 360ms;
}
```

给按钮同时添加 `my-switch` 类。组件样式不设置宿主页面背景，也不依赖在线资源。示例页的 `data-static` 用于固定状态展示，业务组件无需添加。

## 2026-10-13 配色更新与项目复用

用户要求关闭灰色（#737373）、开启绿色（#22C55E），保留金属圆环、细密纹理、浮雕 I/O 与滑动动画。原图保留为造型参考，当前颜色不再声称还原原图。通过 --usl-switch-green / --usl-switch-off 调整两种状态。阴影按宽度等比例缩放，支持 44px / 40px 的业务表单尺寸。

Narrify 的共享 Switch.vue 使用同一 CSS；禁用、busy、v-model、键盘操作保持原机制。此变更针对二态滑动开关，不将勾选框、分段按钮或连续数值滑杆转换为二态控件。
