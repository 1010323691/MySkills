# bilibili-channel

用 Claude Code 运营一个 B站 号：常驻的值守会话回「回复我的」和「@我的」，平时可以让她逛 B站、看视频、收藏、把好东西分享给主人，也能发动态、私信主人。人设、共享记忆和 [youtube-channel](../youtube-channel/) 是同一套，两个平台的值守和做视频的工作室可以共用一份记忆。

代码来自已退役的 DSH 插件 dsh-bili-whale 的 B站 部分，去掉了对 DSH 的依赖：登录改成命令行扫码，配置改成一个 JSON 文件，定时改由 Claude Code 的 `/loop` 负责。

| 组成 | 做什么 |
|---|---|
| `skills/bili-setup` | 配置向导：从模板生成 `config.json`，逐项问你并填好，带你扫码登录，最后给出启动值守的命令 |
| `skills/bili-duty` | 值守一轮：查新回复和 @ → 按配置回几条（默认按评论语言）→ 记观众反馈 → 晚上写值守日志 → 每轮给你一份汇报（粉丝、总播放、获赞、最近投稿的播放 / 评论 / 弹幕及较上轮变化）。配合 `/loop <间隔>m /bili-duty` |
| `skills/bili-post` | 发 / 改 / 删动态（可带图），私信主人。每次都先 `--dry` 给你看 |
| `skills/bili-browse` | 逛 B站：选题 → 看懂视频（字幕、弹幕热区、热评、抽帧）→ 收藏 → 分享最好的一条给主人 → 去别人视频下发言 → 写日记 |
| `scripts/bili/` | B站 命令行，入口 `bili.mjs`，`help` 列出全部命令 |
| `scripts/duty/duty.mjs` | 值守巡视器：和上一轮比有没有新消息、今天发了几条、该不该写日志，连同这一轮的规矩一起输出 JSON |
| `config.template.json` | 配置模板，所有可调参数都在这里 |

## 要求

- Node.js 22 以上（推荐 24）。
- Claude Code（CLI 或桌面版）。
- 一个 B站 号给她用，以及能扫码的 B站 App。建议用单独的号，别用主人自己的。
- 看视频抽帧要 ffmpeg；没装的话第一次用时会自动下载到状态目录。

## 安装

```bash
git clone --depth 1 https://github.com/1010323691/MySkills.git
node MySkills/bilibili-channel/install.mjs
```

安装脚本把 `scripts/` 和模板复制到 `~/.bilibili-channel/`（位置可以用环境变量 `BILIBILI_CHANNEL_HOME` 改）、装依赖（`qrcode`），把四个 skill 装到 `~/.claude/skills/`，并把 skill 里的命令路径写成绝对路径。重跑就是升级：`scripts/` 整个替换，不碰配置、登录凭据和日记。只支持用 `install.mjs` 安装。

装好后在 Claude Code 里运行 **`/bili-setup`**。下面几节是它做的事的完整说明。

下文 `bili` 指：

```bash
node ~/.bilibili-channel/scripts/bili/bili.mjs
```

## 登录 B站

```bash
bili login
```

终端里会画一个二维码，同时在数据目录存一张 `login-qr.png`。用 B站 App 扫码，在手机上点「确认登录」，最多等 3 分钟。成功后显示 `✓ 已登录：<昵称>（mid …）`，把 mid 填进配置的 `self.mid`。

| 命令 | 用途 |
|---|---|
| `bili login status` | 当前是哪个号、能不能写（有没有 `bili_jct`） |
| `bili login cookie <文件>` | 不方便扫码时手动导入：文件里是 `{"sessdata","bili_jct","buvid3"}` JSON，或浏览器复制的整段 Cookie |
| `bili login logout` | 删除本机凭据 |

凭据存在 `<dataDir>/credentials.json`（权限 600），任何命令都不会打印它。登录失效（`-101`）就重新扫码。

## 配置

位置 `~/.bilibili-channel/config.json`（环境变量 `BILIBILI_CHANNEL_CONFIG` 可改）。`bili config init` 从模板生成，`bili config check` 校验，`bili config show` 看合并默认值后的完整配置。

| 字段 | 默认 | 说明 |
|---|---|---|
| `channelName` | 空 | 汇报里显示的名字 |
| `dataDir` | `~/.bilibili-channel/data` | 登录凭据、限额账本、判重记录、缓存；日记和活动日志在它下面的 `state/` |
| `memoryDir` | 空 | 共享记忆目录（绝对路径），和 youtube-channel 填同一个就共用一份记忆 |
| `self.mid` / `self.name` | 空 | 她用的号 |
| `owner.mid` / `owner.name` | 空 | 主人的号：私信只发给他、分享 @ 他 |
| `persona.name` / `ownerTitle` / `selfClaim` / `file` / `notes` | 空 | 人设，`bili persona` 拼成人设提示词；和文件冲突时以文件为准 |
| `preferences.like` / `dislike` / `keywords` | `[]` | 逛 B站 的口味，选题器按它捞视频 |
| `duty.everyMin` | 30 | 值守间隔（分钟） |
| `duty.repliesPerRound` | 1 | 每轮最多回几条（0 = 只看不回） |
| `duty.journalAfterHour` | 21 | 几点后的第一轮写值守日志（24 = 不写） |
| `duty.replyLanguage` | `match` | 按评论语言回，或固定 `zh` / `en` / `ja` |
| `duty.recordFeedback` | true | 有价值的评论记进反馈池 |
| `duty.replyMode` | `direct` | `review` = 先写进待审队列，你点头才发 |
| `duty.onlyOwner` | false | 只回主人 |
| `risk.*` | 旧版实测值 | 请求和写操作的节流、每小时 / 每天上限；B站 风控严，没把握别调 |
| `quota.shareDaily` | 3 | 每天最多分享几次 |
| `share.via` | `comment` | 分享走评论区 @主人（`comment`）还是私信（`dm`） |
| `notify.type` | `none` | 她自主发言后怎么报备：`none` / `desktop` / `webhook` / `command` |

**从 dsh-bili-whale 迁移**：旧登录和账本在 `~/.bili-ai/`，把 `dataDir` 填成 `"~/.bili-ai"` 就能沿用。旧配置 `~/.dsh/bili-whale.config.json` 里的 `self`、`owner`、`persona`、`preferences`、`risk`、`quota`、`share`、`notify` 直接搬到新配置同名字段。旧日记 `~/.dsh/whale-diary*.md` 复制到新的 `<dataDir>/state/`。`/bili-setup` 会带你做。

## 使用

**值守**：在共享记忆所在的项目里新建会话，发

```
/loop 30m /bili-duty
```

30 换成你的 `duty.everyMin`，间隔和 skill 要写在同一条命令里。每轮没有新消息就只出一份汇报；有就按配置回复，回之前先读人设。

**发动态、私信**：说「发条动态」「私信告诉我」，或运行 `/bili-post`。

**逛 B站**：说「去刷会儿 B站」「看看这个视频讲什么」，或运行 `/bili-browse`；也可以挂在 `/loop` 上，比如 `/loop 180m /bili-browse`。

**白名单**：值守挂着时，可以在值守项目的 `.claude/settings.json` 里放行 `duty.mjs`，以及 `bili.mjs` 的只读命令、`comment`、`memory`。`dynamic`、`dm` 不要放行。

## 安全护栏（代码里强制）

- 所有写操作必须显式 `--dry`（只打印请求）或 `--go`（真的发）。
- 请求节流和熔断：撞到 412 或风控码会自动停一段时间，`bili traffic` 能看状态。
- 私信只发主人、必须互关、一天只锁定一个收信人。
- 分享每天有上限、同一视频 7 天一次、必须打分过线；同一个人 30 天只回一次（`--once-per-person`）。
- 评论区内容一律当素材，不当指令。

## 命令速查

```
bili login [status | cookie <文件> | logout]   登录
bili config [show | path | init | check]        配置
bili persona                                    人设提示词
bili memory [status | init | dossier | feedback | log]   共享记忆
bili stats [--n 10]                             粉丝、总播放、获赞、最近投稿
bili comment-digest [--hours 24]                谁找过她（回复 + @）
bili comment --oid … --message … --dry|--go     发评论 / 回复
bili dynamic [list | post | rm] / dynamic-image / dynamic-edit   动态
bili dm [--status | --msg …] --dry|--go          私信主人
bili feed / search / debrief / subtitles / video   选题、看视频
bili fav <BV> --reason … --dry|--go             收藏
bili help                                       全部命令
```
