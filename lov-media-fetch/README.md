# lov-media-fetch — 影视寻宝 · 检索/选源/下载/验收闭环

> 安装方式见[仓库根 README](../README.md)（Claude 与 Codex 通用）。

## 用途

把一句自然语言需求（片名 + 年份 + 版本偏好，如「找这部电影，1080p、中文字幕、版本好一点」）跑成端到端流程：多路独立发现候选 → 版本/画质/体积/字幕/源健康度排序 → 落盘前容量预检 → aria2 多源测速择优下载（支持续传、慢源切换）→ ffprobe 验收（流、时长、字幕覆盖）→ 输出报告并给出确切的本地文件路径。默认以 aria2 为传输后端，qBittorrent 为可选的检索/排队/长期做种适配器。

## 来源

- 基于上游 [lovstudio/media-fetch-skill](https://github.com/lovstudio/media-fetch-skill)（MIT，见 [LICENSE](LICENSE.md)），本目录为完整可用副本（`SKILL.md` + `skills/` 四个子模块 + `scripts/` + `references/` + `assets/` + `kit.yaml`/`skill.yaml`/skill-card），不含上游的 AGENTS.md、CI、测试案例（`cases/`）等仓库级文件。
- 将来升级：拉取上游 `main` 后整体覆盖；`CHANGELOG.md` 用于比对版本。

## 依赖

- Python 3.9+（`scripts/` 下的确定性辅助脚本）
- aria2 1.36+（主传输后端；首次使用时 skill 会引导用系统包管理器安装）
- ffprobe（FFmpeg，最终验收环节）
- 可选：qBittorrent 5.x（WebUI 开 loopback）、Rats Search（独立 DHT 发现）、`lov-subtitle-freedom-skill`（字幕转交，未装则跳过该分支）

## 使用方法

直接说「帮我下载这部电影/这部剧，画质好一点但别太大」「下载导演剪辑版，带中英字幕」。skill 按 `SKILL.md` 中 Step 0–7 的强制流程执行（识别片名 → 候选发现 → 排序消歧 → 容量预检 → 测速下载 → 验收 → 报告）；仅在片名身份含糊、版本内容实质不同、或头部候选难分高下时才会回头问用户。默认字幕偏好为简体中文字幕；目录结构与规则细节见 `references/`。
