# 柔光蓝 · Soft Blue

初始原创按钮示例，用于演示样式保存与静态展示流程；没有参考图片。用户提供图片后新增独立样式目录。

## 设计参数

| 参数 | 值 |
| --- | --- |
| 主色渐变 | `#518cf7` → `#3166da`，垂直渐变 |
| 圆角 | `13px` |
| 最小高度 | `48px` |
| 水平内边距 | `24px` |
| 文字 | 系统字体，`15px`，字重 `600` |
| 投影 | 蓝色柔和投影 + 内侧顶部高光 |
| 展示背景 | `#f0f5ff` |

默认、悬停、按下、焦点、禁用均为原创状态设计。组件 CSS 内使用带前缀的类名与变量，不修改页面的全局按钮样式。

## 使用

引入 [button.css](button.css) 后使用：

```html
<link rel="stylesheet" href="路径/button.css">
<button type="button" class="usl-soft-blue-button">开始创作</button>
<button type="button" class="usl-soft-blue-button" disabled>暂不可用</button>
```

可在业务样式中覆盖变量，例如：

```css
.my-button {
  --usl-button-radius: 20px;
  --usl-button-height: 52px;
}
```

同时为按钮添加 `my-button` 类即可应用覆盖。无需 JavaScript 或第三方依赖；业务点击行为由使用方绑定。

`data-preview-state` 只用于示例页固定展示状态，业务使用时不添加。页面上方带箭头的按钮使用内联 SVG，代码见 [demo.html](demo.html)。
