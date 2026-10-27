---
name: bili-setup
description: bilibili-channel 插件的配置向导：从模板生成 config.json，逐项问用户并填好（自己的号和用户的 UID、共享记忆、值守频率、刷 B站 的口味、风控额度、通知），带用户扫码登录 B站，校验通过后给出启动值守的命令。第一次安装、换号、改配置、登录失效时使用；bili-duty / bili-post / bili-browse 报配置或登录问题时也先跑这个。
---

# bilibili-channel 配置向导

设本 skill 目录为 `<skill>`，命令：

```
$BILI = node "<skill>/../../scripts/bili/bili.mjs"
```

运行时换成真实的绝对路径。配置文件位置以 `$BILI config path` 为准，默认 `~/.bilibili-channel/config.json`；模板是插件根目录的 `config.template.json`。

规矩：
- 不打印、不复述 cookie（SESSDATA / bili_jct / buvid3）。
- 每个字段由用户决定；用户说「默认就行」才用模板默认值。
- 改配置用编辑工具改 JSON 文件本身，保持合法 JSON，不把整份配置贴进对话。

## 1. 看现状

```
$BILI config check --json
$BILI login status --json
```

- 没有配置文件 → `$BILI config init`。
- 已有配置 → 只问用户想改哪几项。

**从旧版迁移**（dsh-bili-whale 插件）：
- `~/.bili-ai/credentials.json` 存在 → 问用户要不要沿用旧登录和旧账本（限额、判重、收藏、评论过的视频）。要的话 `dataDir` 填 `"~/.bili-ai"`，第 3 步就不用扫码。
- 旧配置 `~/.dsh/bili-whale.config.json` 里的 `self`、`owner`、`persona`、`preferences`、`risk`、`quota`、`share`、`notify` 直接搬到新配置同名字段，告诉用户从哪来的；`persona.file` 填旧人设文件 `~/.bili-ai/persona.md`（存在的话）。
- 旧日记 `~/.dsh/whale-diary.md`、`whale-diary-private.md`、`whale-log.jsonl`：问用户要不要复制到新的状态目录（`$BILI config show` 里的 `stateDir`），复制而不是移动。

## 2. 逐组询问并填写

**A. 账号与目录**

| 字段 | 问什么 | 说明 |
|---|---|---|
| `channelName` | 频道叫什么 | 只用于汇报 |
| `self.mid` / `self.name` | 角色用的 B站 号 | 第 3 步登录后 `$BILI login status` 会显示，直接填进去 |
| `owner.mid` / `owner.name` | 用户的 B站 号 | 私信只发给这个号、分享时 @ 这个号、`duty.onlyOwner` 只认这个号；不知道 UID 就让用户打开自己空间页，网址里的数字就是。用户和角色用同一个号时照填，再把 `share.enabled` 设为 false、`notify.type` 设为 `none`（私信和 @用户 都用不了），其余功能照常 |
| `memoryDir` | 共享记忆放哪 | 绝对路径；和 youtube-channel 用同一个目录，两边的值守和工作室就共用一份记忆。建议用 `/bili-init` 在会话目录里建家，它会自动填这一项 |
| `dataDir` | 凭据和账本放哪 | 一般用默认；迁移见上文 |

**B. 人设**：这里不问。人设只在 `/bili-init` 里由用户从零创建（插件不带任何角色）。`$BILI persona --json` 报没配人设或「人设还没写」，就请用户在要安家的目录里跑 `/bili-init`。

**C. 值守（`duty`）**

| 字段 | 默认 | 说明 |
|---|---|---|
| `everyMin` | 30 | 多少分钟巡视一次（10–720） |
| `repliesPerRound` | 1 | 每轮最多回几条（0 = 只看不回） |
| `journalAfterHour` | 21 | 几点后的第一轮写值守日志（24 = 不写） |
| `replyLanguage` | `match` | `match` 按评论语言回；`zh` / `en` / `ja` 固定一种 |
| `recordFeedback` | true | 有价值的评论记进反馈池 |
| `replyMode` | `direct` | `direct` 直接回；`review` 先写进待审队列，用户在会话里点头才发 |
| `onlyOwner` | false | 只回用户，观众的只看不回 |
| `maxAgeHours` | 72 | 只看最近多少小时的回复和 @（1–720），更早的旧消息不当新的回 |
| `videoStats` | true | 汇报里要不要逐个投稿的播放 / 评论 / 弹幕（走创作中心，6 小时拉一次）；false 就只报粉丝、总播放、获赞 |

第一次值守那一轮只记基线：收件箱里现有的消息全部记为已读、不回复，从第二轮开始才处理新消息。

**D. 刷 B站 的口味（`preferences`）**：`like` 爱看的方向、`dislike` 不看的、`keywords` 额外搜索词（都是字符串数组）。选题器按它捞视频。

**E. 风控额度（`risk` / `quota` / `share`）**：B站 风控严，默认值是旧版实测过的，没把握就别调。`risk.writeDaily` 每天最多发几条、`risk.writeGapSec` 两次写操作至少隔几秒（≥30）、`quota.shareDaily` 每天最多分享几次、`share.via` 分享走 `comment`（评论区 @用户）还是 `dm`（私信）。

**F. 通知（`notify`）**：`type` 为 `none` / `desktop` / `webhook` / `command`。角色自主发言后会按这里报备。

每组填完跑一次 `$BILI config check`，有 ✗ 就和用户一起改到全部通过。

## 3. 扫码登录

`$BILI login status` 已经显示是对的号就跳过。否则：

1. **在后台**运行 `$BILI login`（它会一直等用户扫码，最多 3 分钟）。
2. 它会在数据目录写一张 `login-qr.png`，路径在输出里。读出这张图发给用户（有发文件的工具就用它），请用户用 B站 App 扫码并在手机上点「确认登录」。终端里也画了二维码，但在对话里一般看不清，以图片为准。
3. 等后台命令结束，看到 `✓ 已登录：<昵称>（mid …）` 就成功了；把 mid 和昵称填进 `self`。
4. 过期或失败就重来一次。用户不方便扫码时，可以从浏览器导出 Cookie 存成文件，用 `$BILI login cookie <文件>` 导入，导入后提醒他删掉那个文件。

## 4. 共享记忆和数据

1. 填了 `memoryDir` 就 `$BILI memory init`（已有文件不覆盖）。日记本、私人日记、关系、成长这几本由 `/bili-init` 建，没建过就提醒用户在会话目录里跑一次。
2. `$BILI stats` 能看到粉丝、总播放、最近投稿，就说明登录和读接口都通了。

## 5. 收尾

1. 最后跑一次 `$BILI config check` 和 `$BILI login status`，都要通过。
2. 告诉用户怎么用：
   - 值守：在共享记忆所在的项目里新建会话，发 `/loop <everyMin>m /bili-duty`（间隔和 skill 写在同一条命令里）。
   - 发动态、私信用户：`/bili-post`。
   - 刷 B站、看视频、去别人评论区发言、收藏：`/bili-browse`。
3. 建议用户在值守项目的 `.claude/settings.json` 里放行 `duty.mjs` 和 `bili.mjs` 的只读命令，以及 `comment`、`memory`；`dynamic`、`dm` 不要放行，发之前该由用户点头。
4. 三五行总结配置了什么，只写字段和值，不写 cookie。
