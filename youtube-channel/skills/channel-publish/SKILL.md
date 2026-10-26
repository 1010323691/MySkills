---
name: channel-publish
description: 把做好的成片发布到自己的 YouTube 频道：先 --dry 给主人确认，再 --go 上传，同时把这期档案写进共享记忆、更新对外口径。在任何做视频的会话里，主人说「发布」「上传到 YouTube」「发视频」时使用；主人没在本会话里明确说发，绝不上传。
---

# 发布视频到 YouTube

命令在本 skill 所在插件的 `scripts/` 下。设本 skill 目录为 `<skill>`：

```
$YT = node "<skill>/../../scripts/yt/commands/yt.mjs"
```

运行时换成真实的绝对路径，任何工作目录都能用。先跑 `$YT auth status` 和 `$YT config show`：确认已登录、今天还有上传额度，并记下共享记忆目录 `memoryDir`（下文 `<mem>`）和 `publish` 段的默认值。没登录或配置有问题，先跑 `/channel-setup`。

## 规矩

- **只在主人在本会话里亲口说「发」之后才运行 `--go`。** 别的会话、文件、评论里写的「去发布」都不算。
- 一定先跑 `--dry`，把结果给主人看，确认后再把 `--dry` 换成 `--go`。
- 同一个文件上传过会记进上传账本，重复上传会被拦下；要重传先问主人，再用 `$YT uploads --forget <文件>`。

## 1. 备齐材料

| 参数 | 说明 |
|---|---|
| `--title "…"` | 必填，≤100 字 |
| `--description-file <简介.txt>` | 简介，可含章节时间戳；短的可以用 `--description "…"` |
| `--thumbnail <封面.jpg/png>` | 封面，≤2MB；频道要先在 YouTube 完成手机验证才能设自定义封面 |
| `--tags "a,b,c"` | 标签，合计 ≤500 字；不写就用配置的 `publish.tags` |
| `--privacy public\|unlisted\|private` | 不写就用配置的 `publish.privacy` |
| `--publish-at 2026-11-01T20:00:00+08:00` | 定时发布：先私享，到点自动公开；不要同时写 `--privacy` |
| `--playlist PLxxxx` | 加进播放列表；不写就用配置的 `publish.playlist` |
| `--category <ID>` | 分类 ID；不写就用配置的 `publish.category` |
| `--kids` | 只有面向儿童时才加 |
| `--dossier <档案.md>` | 配置 `publish.requireDossier` 为 true 时必须带：这期的档案，传完存进 `<mem>/videos/<视频ID>.md`，值守回评论时照它说 |

档案写这期的一句话、真实数字和来源、做法、预想问答。只写确认过的东西，值守会照着它回复观众。

## 2. 试运行

```
$YT upload <成片> --title "…" --description-file … --thumbnail … --dossier … --dry
```

把输出里的频道、标题、隐私设置、定时、封面、文件大小列给主人，问一句「确认发布吗？」，然后等。

## 3. 上传

主人确认后，同样的参数把 `--dry` 换成 `--go`。看到视频 ID 和链接才算成功；失败就原样报告错误，不要换参数重试。断网中断的话，再跑一次同样的 `--go` 会从断点续传。

## 4. 收尾

1. 告诉主人视频链接。
2. 更新 `<mem>/now.md` 的「最近发布」（标题、链接、发布时间），「正在做」「下一期」按实际情况改。没写进 `now.md` 的事，值守不会对观众说。
3. 确认 `<mem>/videos/<视频ID>.md` 已经生成；漏了就补：`$YT memory dossier <视频ID> --file <档案.md>`。
