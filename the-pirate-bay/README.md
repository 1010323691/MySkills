# the-pirate-bay — The Pirate Bay 检索与磁力提取

> 安装方式见[仓库根 README](../README.md)（Claude 与 Codex 通用）。

## 用途

通过 [apibay.org](https://apibay.org) 公共 JSON API 检索 The Pirate Bay（无需登录、无 CAPTCHA，结果默认按 seeders 降序），提取磁力链接。按意图路由到不同工作流：整季检索（`season`，一次拿全季最优选择）、电影智能搜索（`smart`，自动排 CAM/TS 并按画质+可信度排序）、精确抓取（`grab`，单次 API 调用直出磁力）、浏览（`search`/`top100`）。全部命令支持 `--json` 供 agent 结构化消费，`open` 命令可直接唤起本机 torrent 客户端。

## 来源

- 取自上游 [glittercowboy/taches-cc-resources](https://github.com/glittercowboy/taches-cc-resources) 的 `skills/the-pirate-bay/`（MIT，见 [LICENSE](LICENSE.md)），原样完整副本（`SKILL.md` + `workflows/` + `references/` + `scripts/tpb.ts`），未做修改。
- 将来升级：对照上游同名目录整体覆盖即可。

## 依赖

- Node.js（脚本以 `npx tsx scripts/tpb.ts …` 方式运行，`tsx` 由 npx 按需拉取，无需预装）
- 打开磁力/下载需本机有 torrent 客户端（仅 `open` 命令需要）

## 使用方法

直接说「搜某某电影」「找 1670 第一季的磁力」「把这条 torrent 的 magnet 给我」。典型命令：

```bash
npx tsx scripts/tpb.ts season "1670" --s 1
npx tsx scripts/tpb.ts smart "dark knight rises" --json
npx tsx scripts/tpb.ts grab "ubuntu 24.04" --cat apps
```

选源安全准则（优先 vip/trusted 上传者、核对文件列表与体积、警惕视频包里混 `.exe`）与质量分级见 `references/search-intelligence.md`。
