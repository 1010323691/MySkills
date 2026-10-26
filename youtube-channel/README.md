# youtube-channel

用 Claude Code 运营自己的 YouTube 频道：做视频的会话负责构想、制作和发布，常驻的值守会话负责回评论，两边是同一个「她」，靠一个共享记忆目录接力。

| 组成 | 做什么 |
|---|---|
| `skills/channel-setup` | 配置向导：从模板生成 `config.json`，逐项问你并填好、校验，再带你接通 Google 授权，最后给出启动值守的命令 |
| `skills/channel-duty` | 值守一轮：查新评论 → 按配置回几条（默认按评论语言）→ 记观众反馈 → 晚上给工作室写值守日志 → 每轮给你一份汇报（订阅、总播放、最近视频的播放 / 评论 / 赞及较上轮变化、待回评论、额度）。回复前先读人设提示词。配合 `/loop <间隔>m /channel-duty` 常驻 |
| `skills/channel-publish` | 发布：`--dry` 给主人确认 → `--go` 上传 → 把这期档案写进共享记忆、更新对外口径 |
| `scripts/yt/` | YouTube 命令行：登录、看评论、回复、上传、共享记忆（来自已退役的 DSH 插件 dsh-bili-whale，只保留 YouTube 这一路） |
| `scripts/duty/duty.mjs` | 值守巡视器：和上一轮比有没有新评论、今天回了几条、该不该写日志，连同这一轮的规矩一起输出 JSON 给 skill |
| `config.template.json` | 配置模板。所有可调的参数都在这里，代码里不写死 |

```
做视频的会话 ──/channel-publish──▶ YouTube ◀──/loop 30m /channel-duty── 值守会话
        │                                                          │
        └──────────── 共享记忆目录（now.md / videos / feedback / replies / journal）─┘
```

## 要求

- Node.js 22.21 以上（推荐 24）。要走代理时需要 Node 的 `NODE_USE_ENV_PROXY` 支持。
- Claude Code（CLI 或桌面版）。
- 一个 Google 账号和它名下的 YouTube 频道。

## 安装

```bash
git clone --depth 1 https://github.com/1010323691/MySkills.git
node MySkills/youtube-channel/install.mjs
```

安装脚本做三件事：
1. 把 `scripts/` 和 `config.template.json` 复制到 `~/.youtube-channel/` 并装依赖（`google-auth-library`）。位置可以用环境变量 `YOUTUBE_CHANNEL_HOME` 改。
2. 把三个 skill 复制到 `~/.claude/skills/`。
3. 把 skill 里的命令路径写成绝对路径。

装好后在 Claude Code 里运行 **`/channel-setup`**：它会生成配置、逐项问你、校验，再带你接通 YouTube 授权。下面「配置」「接通 YouTube」两节是它做的事的完整说明，想手动配置也可以照着做。

重跑安装脚本就是升级：`scripts/` 会整个替换，不会碰你的配置、令牌和共享记忆。加 `--dry` 只打印要做什么，不实际执行。

只支持用 `install.mjs` 安装。直接把 skill 目录复制过去不行：命令行脚本需要 `npm install` 装依赖，skill 里的命令路径也要由安装脚本写成绝对路径。

下文 `yt` 指：

```bash
node ~/.youtube-channel/scripts/yt/commands/yt.mjs
```

## 接通 YouTube（第一次装时做一次）

插件用你自己在 Google Cloud 建的 OAuth 客户端登录，令牌只存在本机。全程大约 10 分钟。

### 1. 建 Google Cloud 项目，启用 API

1. 打开 <https://console.cloud.google.com/>，左上角项目下拉框 → **新建项目**，名字随意，比如 `my-channel`。
2. 进入这个项目，打开 **API 和服务 → 库**，搜索 **YouTube Data API v3** → **启用**。

### 2. 配置 OAuth 同意屏幕

打开 **API 和服务 → OAuth 同意屏幕**。新版界面叫 **Google Auth Platform**，分「品牌塑造 / 目标对象 / 数据访问」几个页。

1. **用户类型**选「外部」（个人 Google 账号只能选这个）。
2. 应用名称随意；用户支持邮箱和开发者联系邮箱填你自己的。
3. **数据访问**页的范围可以不加，登录时插件会申请 `https://www.googleapis.com/auth/youtube.force-ssl`（管理你的 YouTube 账号）。想写清楚就手动加上这一条。
4. **目标对象**页，二选一：
   - **保持「测试」状态**，并在「测试用户」里加上拥有频道的那个 Google 账号。⚠ 测试状态下的令牌 **7 天就会失效**，每周要重新 `yt auth login` 一次。
   - **点「发布应用」，改成「正式版」**（推荐，自用就够了，不用提交 Google 审核）。令牌长期有效，代价是登录时会看到「Google 尚未验证此应用」，点 **高级 → 转到 …（不安全）** 继续即可。

### 3. 建 OAuth 客户端，下载 JSON

1. 打开 **API 和服务 → 凭据**（新版是 **客户端**）→ **创建凭据 → OAuth 客户端 ID**。
2. **应用类型选「桌面应用」**。必须是这个：插件用 `http://127.0.0.1:<随机端口>` 回环地址接收授权，桌面应用类型不用配置重定向 URI。
3. 创建后点 **下载 JSON**，得到 `client_secret_xxx.json`。

### 4. 导入客户端、登录

```bash
yt auth client ~/Downloads/client_secret_xxx.json
yt auth login
```

1. `auth login` 会自动打开浏览器；没打开就复制终端里打印的地址自己打开。最多等 5 分钟。
2. 选择**拥有频道的那个账号**。如果频道是品牌账号，在账号选择页选频道的名字。
3. 看到「Google 尚未验证此应用」就点 **高级 → 转到 …（不安全）**。
4. 权限页**一定要勾上**「查看、修改和永久删除您的 YouTube 视频、评分、评论和字幕」，没勾的话插件会报错让你重来。
5. 终端显示 `✓ 已登录 YouTube 频道：<频道名>（<频道ID>）` 就是登录成功了。

导入后下载的那份 JSON 可以删掉（里面有 client_secret），插件已经存了一份副本。

### 5. 检查

```bash
yt auth status
```

应该看到「OAuth 客户端 ✓」「登录 ✓ <频道名>」，以及今天的配额。

### 令牌存在哪

| 文件 | 内容 |
|---|---|
| `<dataDir>/youtube-client.json` | 导入的 OAuth 客户端（含 client_secret） |
| `<dataDir>/youtube-token.json` | 访问令牌和刷新令牌，过期自动刷新 |
| `<dataDir>/youtube-state.json` | 今日配额计数、暂停状态 |
| `<dataDir>/youtube-replied.json` | 回复判重账本，同一条评论不会回两次 |
| `<dataDir>/youtube-uploads.json` | 上传账本，用于断点续传和防重复上传 |

`<dataDir>` 默认是 `~/.youtube-channel/data`。这些文件都别提交到 git，也别发给别人；换机器时把整个目录拷过去就能带走登录。退出登录用 `yt auth logout`，它会同时撤销 Google 那边的授权。

### 常见问题

| 现象 | 处理 |
|---|---|
| 一周后突然要重新登录 | 同意屏幕还是「测试」状态，按第 2 步发布成正式版，再 `yt auth login` |
| `access_denied` 或「此应用尚未完成 Google 验证流程」 | 测试状态下没把这个账号加进「测试用户」 |
| 报「没有勾选管理你的 YouTube 账号权限」 | 重新 `yt auth login`，在权限页勾上那一项 |
| 连不上 Google（国内网络） | 配置里写 `proxy`，例如 `http://127.0.0.1:7890`，或者设置环境变量 `HTTPS_PROXY` |
| 上传后视频被锁成私享 | YouTube 对未经审核的 API 项目上传的视频可能限制为私享；需要的话在 Google 提交 YouTube API 审核（API Services Audit） |
| 设不了自定义封面 | 频道要先在 YouTube 完成手机号验证 |
| 配额用完 | 官方默认每天 10,000 单位，太平洋时间零点重置；插件按配置的 `limits.dailyUnits`（默认 8,000）留余量 |

## 配置

所有参数都在一个 JSON 文件里：

- 位置：`~/.youtube-channel/config.json`。可以用环境变量 `YOUTUBE_CHANNEL_CONFIG` 指定别的文件，`yt config path` 显示实际用的是哪个。
- 生成：`yt config init` 从模板复制一份，已有的不覆盖。
- 校验：`yt config check` 列出每个问题，没问题时显示 ✓。`yt config show` 显示合并默认值之后的完整配置。
- 推荐用 `/channel-setup` 填写，它会一项项问你。

模板（[config.template.json](./config.template.json)）：

```json
{
  "channelName": "",
  "dataDir": "~/.youtube-channel/data",
  "memoryDir": "",
  "persona": {
    "name": "",
    "ownerTitle": "",
    "selfClaim": "",
    "file": "",
    "notes": []
  },
  "proxy": "",
  "limits": {
    "writeDaily": 30,
    "writeGapSec": 120,
    "uploadDaily": 10,
    "dailyUnits": 8000,
    "minGapMs": 1000
  },
  "duty": {
    "everyMin": 30,
    "repliesPerRound": 1,
    "journalAfterHour": 21,
    "replyLanguage": "match",
    "recordFeedback": true
  },
  "publish": {
    "privacy": "public",
    "category": "",
    "playlist": "",
    "tags": [],
    "language": "",
    "audioLanguage": "",
    "requireDossier": true
  }
}
```

| 字段 | 默认 | 说明 |
|---|---|---|
| `channelName` | 空 | 频道名，只用于显示 |
| `dataDir` | `~/.youtube-channel/data` | 令牌、账本、活动日志放在这里；写绝对路径，相对路径按配置文件所在目录解析 |
| `memoryDir` | 空 | 共享记忆目录，**绝对路径**（可以用 `~` 开头）。建议放在做视频的项目里；填好后运行 `yt memory init` |
| `persona.name` | 空 | 角色名，比如 Rei |
| `persona.ownerTitle` | 空 | 怎么称呼主人，比如 partner |
| `persona.selfClaim` | 空 | 怎么自称，比如 I |
| `persona.file` | 空 | 人设文件（Markdown 全文）；和上面三项冲突时以文件为准 |
| `persona.notes` | `[]` | 补充说明，每条一句 |
| `proxy` | 空 | 访问 Google 的代理，例如 `http://127.0.0.1:7890`；留空 = 直连，也会读环境变量 `HTTPS_PROXY` |
| `limits.writeDaily` | 30 | 每天最多回几条（1–100） |
| `limits.writeGapSec` | 120 | 两条回复至少隔几秒（≥30） |
| `limits.uploadDaily` | 10 | 每天最多上传几个（0 = 禁止上传，`--go` 会直接被拒） |
| `limits.dailyUnits` | 8000 | 每天最多用多少 API 配额（官方默认 10000） |
| `limits.minGapMs` | 1000 | 两次 API 请求的最小间隔 |
| `duty.everyMin` | 30 | 值守间隔（分钟，10–720），用于 `/loop` |
| `duty.repliesPerRound` | 1 | 每轮最多回几条（0 = 只看不回） |
| `duty.journalAfterHour` | 21 | 几点以后的第一轮写值守日志（24 = 不写） |
| `duty.replyLanguage` | `match` | `match` 按评论语言回；`en` / `ja` / `zh` 固定一种 |
| `duty.recordFeedback` | true | 有价值的评论记进反馈池 |
| `publish.privacy` | `public` | 上传默认可见性；定时发布时自动改为私享 |
| `publish.category` | 空 | 默认分类 ID（28 科技、27 教育、22 人物和博客） |
| `publish.playlist` | 空 | 默认加进的播放列表 ID |
| `publish.tags` | `[]` | 每期都带的标签 |
| `publish.language` | 空 | 默认的标题简介和音轨语言，如 `en`、`ja`、`zh-Hans` |
| `publish.audioLanguage` | 空 | 音轨语言和标题语言不同时才填 |
| `publish.requireDossier` | true | 上传必须带 `--dossier` 档案（设了 memoryDir 才生效） |

命令行参数优先于配置里的默认值。

**人设提示词**：`yt persona` 把 `persona` 段和人设文件拼成一段提示词。值守回复评论、写值守日志，发布时写标题和简介，都先读它，所以对外说话始终是同一个角色。1.1 版的 `personaFile` 仍然兼容，`config check` 会提示改成 `persona.file`。

**从 dsh-bili-whale 迁移**：旧登录在 `~/.bili-ai/`，把 `dataDir` 填成 `"~/.bili-ai"` 就能直接沿用，不用重新授权。旧配置 `~/.dsh/bili-whale.config.json` 不再读取，里面 `youtube` 段的值要搬到新配置的 `memoryDir`、`proxy` 和 `limits` 里；`persona` 段的 `name`、`ownerTitle`、`selfClaim` 搬到新配置的同名字段，`~/.bili-ai/persona.md` 填进 `persona.file`。`/channel-setup` 会检测到旧数据并带你迁移。

## 共享记忆

`yt memory init` 会在配置的 `memoryDir` 下生成以下文件，约定写在其中的 `README.md` 里：

| 文件 | 谁写 | 谁读 |
|---|---|---|
| `now.md` | 工作室（每次收工更新） | 值守：这里没写的不对观众承诺 |
| `videos/<视频ID>.md` | 发布时用 `--dossier` 写入 | 值守：回这期评论前读，数字以它为准 |
| `feedback.md` | 值守巡视时追加 | 工作室：构想下一期前读，用掉的打勾 |
| `replies.md` | 每次回复成功后自动追加 | 工作室：避免和评论区的说法矛盾 |
| `journal.md` | 值守每晚记 1–3 句 | 工作室：开工时读 |

建议在做视频的项目的 `CLAUDE.md` 里写一句：「开工先读 `<memoryDir>/journal.md` 和 `feedback.md`，收工更新 `now.md`」。

## 使用

**值守**：在桌面版新建一个会话，工作目录放在共享记忆所在的项目，然后发送（30 换成你配置的 `duty.everyMin`）

```
/loop 30m /channel-duty
```

间隔和 skill 要写在**同一条命令**里。只写 `/loop 30m` 会进入通用的自主巡检，不会去查评论。

- 每轮先看有没有新评论，没有就一句话结束；有就按 `duty.repliesPerRound` 挑几条回。
- `duty.journalAfterHour` 之后的第一轮写值守日志，一天一次。
- 改了配置不用重启循环，下一轮就按新配置执行；只有改 `everyMin` 时要重新发一次 `/loop`。
- 要求：桌面应用一直开着，电脑不睡眠；`/loop` 7 天后过期，到时重发一次。

**发布**：在做视频的会话里说「发布到 YouTube」，或运行 `/channel-publish`。它会先给你看 `--dry` 的结果，你确认了才真的上传。

**多语言**：

| 想要 | 插件能不能做 | 怎么做 |
|---|---|---|
| 多语言字幕 | ✓ | 上传时 `--caption en=en.srt --caption ja=ja.vtt`；已发布的视频用 `yt caption <视频ID> …`。每条 400 配额单位 |
| 多语言标题和简介 | ✓ | 先 `--language en` 设主语言，再 `--localize ja=ja.txt`（第一行标题，其余简介）；已发布的视频用 `yt localize <视频ID> …` |
| 标记音轨语言 | ✓ | `--language` 或 `--audio-language` |
| 多语言音轨（配音） | ✗ | YouTube API 没有这个接口。到 YouTube Studio → 视频 → 语言 → 添加语言 → 上传纯音频文件；频道要开通高级功能 |

**白名单**：值守会话挂着时，每次运行命令弹授权提示会让循环卡住。可以在值守项目的 `.claude/settings.json` 里放行：

```json
{
  "permissions": {
    "allow": [
      "Bash(node ~/.youtube-channel/scripts/duty/duty.mjs:*)",
      "Bash(node ~/.youtube-channel/scripts/yt/commands/yt.mjs inbox:*)",
      "Bash(node ~/.youtube-channel/scripts/yt/commands/yt.mjs reply:*)",
      "Bash(node ~/.youtube-channel/scripts/yt/commands/yt.mjs memory:*)"
    ]
  }
}
```

路径按 skill 里实际写的格式填。`upload` 不要放行，发布本来就该由你确认。

## 命令速查

```
yt config [show|path|init|check]       配置文件
yt auth client <客户端.json> | login [--no-open] | status | logout
yt videos [--n 10]                     自己频道最近的视频
yt stats [--n 10]                      频道数据：订阅、总播放、最近视频的播放 / 评论 / 赞
yt persona                             人设提示词（回复前先读）
yt comments <视频ID> [--n 20]          某个视频的评论
yt inbox [--unreplied] [--json]        整个频道的评论收件箱
yt thread <楼ID>                       一整条楼
yt reply <评论ID> --message "…" --dry|--go
yt upload <视频> --title "…" [参数] --dry|--go
yt uploads [--forget <文件>]           上传账本
yt captions <视频ID>                   已有字幕
yt caption <视频ID> --caption en=字幕.srt … --dry|--go     补字幕
yt localize <视频ID> --language en --localize ja=文件 … --dry|--go   设语言、补多语言标题简介
yt memory [status|init|dossier|feedback|log]
```

所有读命令都可以加 `--json`。
