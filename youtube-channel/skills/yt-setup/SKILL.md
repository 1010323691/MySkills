---
name: yt-setup
description: youtube-channel 插件的配置向导：从模板生成 config.json，逐项问用户并填好（频道、共享记忆目录、人设、代理、值守频率与每轮回复数、额度、发布默认值），校验通过后引导接通 Google / YouTube 授权，最后给出启动值守的命令。第一次安装、改配置、换机器、授权失效时使用；yt-duty 或 yt-publish 报配置问题时也先跑这个。
---

# youtube-channel 配置向导

设本 skill 目录为 `<skill>`，命令：

```
$YT = node "<skill>/../../scripts/yt/commands/yt.mjs"
```

运行时换成真实的绝对路径。配置文件的位置以 `$YT config path` 的输出为准，默认是 `~/.youtube-channel/config.json`；模板在插件根目录的 `config.template.json`。

规矩：
- 不打印令牌、client_secret，也不把客户端 JSON 的内容读出来复述。
- 每个字段都由用户决定。用户说「默认就行」才用模板里的默认值。
- 改配置用编辑工具改 JSON 文件本身，保持合法 JSON；不要把整份配置贴进对话。

## 1. 看现状

```
$YT config check --json
$YT auth status --json
```

- 配置文件不存在 → `$YT config init`，从模板生成。
- 已经有配置 → 只问用户想改哪几项，跳到第 2 步对应的组。

**从旧版迁移**（dsh-bili-whale 插件）：如果 `~/.bili-ai/youtube-token.json` 存在，问用户要不要沿用旧的登录。
- 要的话：`dataDir` 填 `"~/.bili-ai"`，第 4 步就不用重新授权。
- 旧配置 `~/.dsh/bili-whale.config.json` 里 `youtube` 段的 `memoryDir`、`proxy`、`writeDaily`、`writeGapSec`、`uploadDaily`、`dailyUnits` 可以拿来当默认值，并告诉用户这些值是从哪来的。
- 旧配置里的 `persona.name` / `persona.ownerTitle` / `persona.selfClaim` 直接搬到新配置的同名字段；旧人设文件 `~/.bili-ai/persona.md` 填进 `persona.file`。旧配置的 `preferences`（喜欢 / 讨厌的 B站内容）是给刷 B站用的，不迁移，除非用户想把其中几条写进 `persona.notes`。

## 2. 逐组询问并填写

一组一组问，能给选项就给选项，并把推荐项放第一个。

**A. 频道与目录**

| 字段 | 问什么 | 说明 |
|---|---|---|
| `channelName` | 频道叫什么 | 只用于显示和总结 |
| `memoryDir` | 共享记忆放哪 | 绝对路径，可以用 `~` 开头。建议放在做视频的项目里，比如 `<项目>/memory`。留空 = 值守和工作室不共享记忆，不推荐 |
| `persona.name` | 角色叫什么 | 对外的名字，用户自己定 |
| `persona.ownerTitle` | 角色怎么称呼用户 | 用户自己定 |
| `persona.selfClaim` | 角色怎么自称 | 用户自己定 |
| `persona.file` | 有没有人设文件 | Markdown 全文。已经用 `/bili-init` 建过人设就填同一个文件，两个平台共用一个角色；没有的话和用户一起从零写一份 |
| `persona.notes` | 还有什么要补充 | 字符串数组，每条一句，用户想到什么写什么 |

人设完全由用户定：插件不带任何角色，你只按「名字 → 称呼 → 角色是什么、和用户什么关系 → 性格 → 说话方式 → 喜欢和不喜欢 → 底线」的顺序提问并整理成文字，不提供现成角色、不自己补设定；用户想不出来时请用户说说想要的感觉，写两三种方向让用户挑。用户跳过的留空。不冒充真人、不编数字这类硬规矩在 skill 里，不用写进人设。

这几项会被 `$YT persona` 拼成一段人设提示词，值守回复和发布写简介前都先读它。填完运行一次 `$YT persona` 给用户看效果。
| `dataDir` | 令牌和账本放哪 | 一般用默认值；迁移时见上文 |
| `proxy` | 访问 Google 要不要代理 | 国内网络一般要，格式 `http://127.0.0.1:7890`；留空 = 直连 |

**B. 值守（`duty`）**

| 字段 | 默认 | 说明 |
|---|---|---|
| `everyMin` | 30 | 多少分钟巡视一次（10–720），用于 `/loop` 的间隔 |
| `repliesPerRound` | 1 | 每轮最多回几条（0 = 只看不回，只记反馈） |
| `journalAfterHour` | 21 | 几点以后的第一轮给工作室写值守日志（0–23；24 = 不写） |
| `replyLanguage` | `match` | `match` = 按评论的语言回；`en` / `ja` / `zh` = 固定用一种语言 |
| `recordFeedback` | true | 有价值的评论要不要记进反馈池 |

**C. 额度（`limits`）**

| 字段 | 默认 | 说明 |
|---|---|---|
| `writeDaily` | 30 | 每天最多回几条（1–100） |
| `writeGapSec` | 120 | 两条回复至少隔几秒（≥30） |
| `uploadDaily` | 10 | 每天最多上传几个（0 = 禁止上传） |
| `dailyUnits` | 8000 | 每天最多用多少 API 配额（官方默认上限 10000） |

**D. 发布默认值（`publish`）**：命令行参数会覆盖这些默认值。

| 字段 | 默认 | 说明 |
|---|---|---|
| `privacy` | `public` | `public` / `unlisted` / `private`；定时发布时自动改为私享 |
| `category` | 空 | YouTube 分类 ID，比如 28 = 科技、27 = 教育、22 = 人物和博客 |
| `playlist` | 空 | 默认加进的播放列表 ID（PLxxxx） |
| `tags` | `[]` | 每期都带的标签 |
| `language` | 空 | 默认的标题简介和音轨语言（如 `en`）；要发多语言标题时必须有 |
| `audioLanguage` | 空 | 音轨语言和标题语言不同时才填 |
| `aiDisclosure` | null | AI 合成内容声明的默认值：true / false / null（不声明）。看起来真实的 AI 生成或改动内容（让真人说没说过的话、改真实事件的画面、生成以假乱真的场景、AI 生成的音乐是视频主体）必须声明；明显不真实的动画和图表、AI 只用来写脚本 / 标题 / 封面、调色滤镜、画质修复、克隆自己的声音配音不用声明。按频道内容问用户 |
| `requireDossier` | true | 上传时必须带 `--dossier` 档案（设了 memoryDir 才生效） |

每组填完运行一次 `$YT config check`，有 ✗ 就和用户一起改到全部通过。

## 3. 初始化共享记忆

填了 `memoryDir` 就运行 `$YT memory init`。已有的文件不会被覆盖。

如果做视频的项目有 `CLAUDE.md`，建议用户加一句：「开工先读 `<memoryDir>/journal.md` 和 `feedback.md`，收工更新 `now.md`」。这句要经用户同意才写。

## 4. 接通 YouTube 授权

`$YT auth status` 显示已登录、频道也对，就跳过这一步。否则带用户一步步做，每步确认做完再进入下一步：

1. 在 <https://console.cloud.google.com/> 新建项目，进入 **API 和服务 → 库**，启用 **YouTube Data API v3**。
2. 打开 **OAuth 同意屏幕**（Google Auth Platform）：
   - 用户类型选「外部」，填应用名称和邮箱。
   - 在「目标对象」里**发布应用（改成正式版）**。保持「测试」状态的话，令牌 7 天就失效；如果用户坚持用测试状态，要把频道所属账号加进「测试用户」。
3. 打开 **凭据 → 创建凭据 → OAuth 客户端 ID**，**应用类型选「桌面应用」**，然后下载 JSON。
4. 问用户 JSON 下载到了哪里，运行 `$YT auth client "<路径>"`。成功后提醒用户可以删掉下载的那份。
5. 运行 `$YT auth login`。它会打开浏览器，最多等 5 分钟：
   - 选拥有频道的那个账号；频道是品牌账号的话选频道名。
   - 看到「Google 尚未验证此应用」时点 **高级 → 转到 …（不安全）**。
   - 权限页**勾上** YouTube 那一项。
6. 运行 `$YT auth status`，确认频道名对。

报错时对照插件 README 的「常见问题」一节处理：`access_denied`、连不上 Google、没勾选权限等。

## 5. 收尾

1. 最后运行一次 `$YT config check` 和 `$YT auth status`，两个都要通过。
2. 告诉用户怎么启动值守：在共享记忆所在的项目里新建一个会话，发送 `/loop <everyMin>m /yt-duty`。间隔和 skill 要写在同一条命令里。
3. 建议用户在值守项目的 `.claude/settings.json` 里放行 `duty.mjs`，以及 `yt.mjs` 的 `inbox`、`reply`、`memory` 子命令，避免挂着时卡在授权提示上。`upload` 不要放行。
4. 用三五行总结配置了什么，只写字段和值，不写令牌。
