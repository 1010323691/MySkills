# torrentclaw — TorrentClaw 影视 torrent 检索与下载

> 安装方式见[仓库根 README](../README.md)（Claude 与 Codex 通用）。

## 用途

通过 [TorrentClaw](https://torrentclaw.com) API 聚合 30+ torrent 来源（YTS、EZTV、Knaben、Prowlarr、Bitmagnet 等，含 TMDB 元数据）检索电影/电视剧，按画质（480p–2160p）、类型、年份、语言、HDR、音频、季/集（`S01E05`/`1x05`）筛选，结果带评分与 0–100 质量分。检测到本机 Transmission / aria2 时可直接把磁力丢给客户端，否则提供磁力链接复制、`.torrent` 下载或客户端安装指引。

## 来源

- 基于上游 [torrentclaw/torrentclaw-skill](https://github.com/torrentclaw/torrentclaw-skill)（MIT，见 [LICENSE](LICENSE.md)），本目录为完整可用副本（`SKILL.md` + `scripts/` + `references/`），不含上游的 CI、CONTRIBUTING 等仓库级文件。
- 将来升级：拉取上游 `main` 后整体覆盖 `SKILL.md` / `scripts/` / `references/`（`CHANGELOG.md` 用于比对版本）。

## 依赖

- `bash` + `curl`（+ `jq` 用于格式化），Windows 下用 Git Bash / WSL
- 下载需本机装有 Transmission（`transmission-remote` 在 PATH）或 aria2（RPC 端口 6800）；都没有时 skill 只输出磁力/文件，并给出安装指引
- 无需 API key（匿名 30 次/分钟）；高频使用可申请 key 放环境变量 `TORRENTCLAW_API_KEY`

## 使用方法

直接对 agent 说：「找某某电影 1080p 的磁力」「搜 breaking bad S05E14」「把这条 torrent 加到 Transmission」。skill 会按 `detect-client.sh` → API 检索 → 表格呈现 → 用户选择后 `add-torrent.sh` 的固定流程执行；API 细节见 `references/api-reference.md`。
