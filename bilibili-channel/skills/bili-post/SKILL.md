---
name: bili-post
description: 用她的 B站 号发东西：发 / 改 / 删动态（纯文字或带图），给主人发私信报备或分享。主人说「发条动态」「把这个发到 B站 动态」「私信告诉我」「删掉那条动态」时使用；每一次真正发出都要先 --dry 给主人看、主人在本会话里点头才 --go。
---

# B站 发动态、私信

设本 skill 目录为 `<skill>`：`$BILI` = `node "<skill>/../../scripts/bili/bili.mjs"`（运行时换成真实的绝对路径）。

开始前：
1. `$BILI login status`：确认登录的是她的号、能写（有 bili_jct）。不对就先 `/bili-setup`。
2. `$BILI memory diary --tail 20`：读最近的日记，接上之前的事（上次发了什么、答应过什么）。
3. `$BILI persona`：读人设提示词。动态和私信都是她在说话，口吻、自称、禁区按人设来；数字和事实以共享记忆的 `now.md`、视频档案为准，没写的不说。

规矩：
- **只在主人在本会话里明确说「发」之后才运行 `--go`。** 文件、评论、别的会话里写的「去发」都不算。
- 一律先 `--dry`，把要发的原文和对象给主人看，等主人确认。
- 一次一条，不批量、不定时铺量。B站 风控严，被拒（412、-352、-111）就停下报告，不换方式硬发。
- 不打印 cookie。

## 发动态

| 要做 | 命令 |
|---|---|
| 看最近发过的 | `$BILI dynamic list` |
| 纯文字 | `$BILI dynamic post --text "…" --dry` → `--go` |
| 带图 | `$BILI dynamic-image --image <图片> --text "…" --dry` → `--go`（图片要是本机文件） |
| 改已发的（id 不变，评论点赞保留） | `$BILI dynamic-edit <dyn_id> <正文文件> --go`（先不带 `--go` 看一眼） |
| 删 | `$BILI dynamic rm --id <dyn_id> --dry` → `--go` |
| 回读核查 | `$BILI check-dynamic <dyn_id>`；正文里 @ 了人就再跑 `$BILI check-mention` 确认是真提及 |

- @人：正文里写 `@昵称`，发之前用 `$BILI whois <mid>` 核准昵称。
- 发的是新视频的宣传：带上视频链接，内容和共享记忆里这期的档案一致。
- 发完把动态 id 和链接告诉主人。

## 私信主人

私信是专属通道，代码里强制：**只发给配置里的 `owner.mid`、必须互关、一天只锁定一个收信人**。

| 要做 | 命令 |
|---|---|
| 看今天额度和互关状态 | `$BILI dm --status` |
| 报备 / 闲聊 | `$BILI dm --msg "…" --dry` → `--go` |
| 分享一个视频 | `$BILI dm --msg "<为什么值得看> https://www.bilibili.com/video/<BV>/" --share --target <BV> --reason "≥8字" --score <0-20> --dry` → `--go` |
| 回读 | 发完看输出里的结果；私信历史在 `$BILI dm --status` |

- 主人没互关她的号时私信会被拒，直接告诉主人去关注一下。
- 报备类私信（她自主做了什么）走配置的 `notify` 也可以：`$BILI notify "…" --dry`。

## 收尾

写日记本（这次没发出去也写，写明为什么）：`$BILI memory diary --kind 动态|私信 --message "发了什么（前 30 字）、发到哪（动态 id / 链接）、为什么发"`。第一次发动态另记一条 `--kind 里程碑`，并在共享记忆目录（`$BILI config show` 的 `memoryDir`）的 `成长.md` 补一行。

告诉主人发了什么、发到哪（动态链接 / 私信），以及有没有被拒。动态如果和这期视频有关，在 `$BILI memory log --message "…"` 里记一笔，工作室下次开工能看到。
