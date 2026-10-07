# JavBus-GetMagnet — JavBus 磁力链接与封面图

> 安装方式见[仓库根 README](../README.md)（Claude 与 Codex 通用）。

## 用途

抓取 JavBus（javbus.com）磁力链接与封面图：按女演员（star id，如 `138y`，或姓名）或单个番号。自动通过 18+ 年龄验证门，每个作品选最小 1080p（无则 720p），下载封面，并生成自包含展示页（`data.json` + `magnets.txt` + `covers/` + `index.html`）。`--serve` 可本地起服务，页面「获取更新」按钮能检查新作品。

## 来源

自制（基于 javbus.com 实际抓取流程的完整实现），无上游。

## 依赖

- Python 3，仅标准库（无第三方依赖），入口 `scripts/javbus_get_magnet.py`
- 可访问 javbus.com 的网络
- `cookies.txt`（年龄验证 + 会话缓存）为本地文件，**不在本仓库中**（被本目录 `.gitignore` 忽略），首次运行自动清门生成；验证门重现或结果异常为空时删除该文件重跑即可

## 使用方法

直接说「给我 XX 的磁力链接和封面」。典型命令：

```bash
python scripts/javbus_get_magnet.py --star 138y
python scripts/javbus_get_magnet.py --name 瀬戸環奈
python scripts/javbus_get_magnet.py --code SNOS-313
python scripts/javbus_get_magnet.py --serve <数据文件夹>   # 本地服务 + 获取更新按钮
```

完整字段规格、输出格式与失败处理见 `SKILL.md`。
