# movie-magnet-hunt — 片单批量磁力链接

> 安装方式见[仓库根 README](../README.md)（Claude 与 Codex 通用）。

## 用途

给一组电影/剧集名（日文/韩文/中文/英文混写），跨三个站点批量查找磁力下载链接：sidhub.cc（PT 系磁力）、番号楼 fanhaolou.com（全网磁力索引）、6V/6vw.cc（旧帖记录）。默认「1080p 中文字幕优先」，自动消歧同名片、验证磁力有效性，输出 `资源清单.md` + `magnets.txt`（可直接导入下载工具）。

不适用：要网盘直链分享页、在线观看、或 JAV 番号（后者用 [JavBus-GetMagnet](../JavBus-GetMagnet/)）。

## 来源

自制，2026-10-07 实战踩坑固化：Referer、编码、URL 转义、ZBLOG 参数、base64 磁力等坑都写在 `scripts/` 里。先跑通脚本再谈手工兜底，手工时必须遵守 `SKILL.md` 的决策规则与禁止事项。

## 依赖

- Python 3（须为真解释器：Windows 上 `python3` 常是 WindowsApps stub，静默失败、退出码 49；前置检查见 `SKILL.md`）
- 三站网络连通：开工前须探测，各站全 200 才开始
- TMDB API 凭证（推荐）：系统环境变量 `TMDB_API_TOKEN` / `TMDB_API_KEY`，供 `scripts/tmdb_normalize.py`
  在第 1 步自动规范化片名（多语言规范片名 / 年份 / 产地 / 主演）；未设置或失效时降级手工规范化，不阻塞。
  API 使用链路与字段坑见 `SKILL.md` 的「TMDB API 使用链路」一节

`evals/` 为本 skill 的评测案例。

## 使用方法

直接说「帮我找这些电影的磁力/资源」「1080p 中文字幕」。
