# convert-chm-to-txt — CHM 转常规 txt

## 用途

把 CHM（Microsoft HTML Help）文件转换成记事本可直接打开的常规 txt。自动识别三种内部结构：

1. **网页阅读器式**（电子书最常见）：章节文件是 GBK 编码的 `document.write("HTML")` 脚本，另有一份 `js/page.js` 章节表记录卷/章顺序 → 输出 `全书.txt`（合并全文）、`目录.txt`、`chapters/`（每章一个）、`images/`（封面）。
2. **标准 HTML Help**：一批 `.htm/.html` 页面 → 保留原相对路径，每页转一个 `.txt`（script/style 和标签已去除）。
3. **纯文本打包**：`.txt` + 图片 → 重新编码 UTF-8（BOM）原样输出。

输出文本统一 UTF-8 带 BOM，Windows 记事本 / Word 双击即可正确显示中文。

## 使用方法

对 agent 说即可（触发 [SKILL.md](SKILL.md)），例如：

- 「把 01.chm 转换成常规的 txt」
- 「这个 CHM 转成 txt，输出到 D:\xxx」

也可以直接跑脚本（需先有 7-Zip，`winget install 7zip.7zip -e --silent --disable-interactivity` 可装）：

```bash
python scripts/convert_chm_to_txt.py "D:\path\to\01.chm" "D:\path\to\01_txt"
```

## 产物示例（阅读器式）

```
01_txt/
├── 全书.txt        # 按卷/章顺序合并的全文
├── 目录.txt        # 书名 + 各卷 + 各章标题
├── chapters/       # 每章一个纯文本 .txt
└── images/         # 各卷封面图片
```

## 边界

- 不修改源 .chm，解包走系统临时目录、结束即清理。
- 不做图片 OCR、不做图文混排；图片仅随文件保留。
- 章节表语法与内置 `pages[N]=[...]` 不同的 CHM，需先查看其 js 后调整 `parse_pages`。
