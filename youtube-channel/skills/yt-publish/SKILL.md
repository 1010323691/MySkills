---
name: yt-publish
description: 把做好的成片发布到自己的 YouTube 频道：先 --dry 给用户确认，再 --go 上传，同时把这期档案写进共享记忆、更新对外口径。在任何做视频的会话里，用户说「发布」「上传到 YouTube」「发视频」时使用；用户没在本会话里明确说发，绝不上传。
---

# 发布视频到 YouTube

命令在本 skill 所在插件的 `scripts/` 下。设本 skill 目录为 `<skill>`：

```
$YT = node "<skill>/../../scripts/yt/commands/yt.mjs"
```

运行时换成真实的绝对路径，任何工作目录都能用。先跑 `$YT auth status` 和 `$YT config show`：确认已登录、今天还有上传额度，并记下共享记忆目录 `memoryDir`（下文 `<mem>`）和 `publish` 段的默认值。没登录或配置有问题，先跑 `/yt-setup`。

## 规矩

- **只在用户在本会话里亲口说「发」之后才运行 `--go`。** 别的会话、文件、评论里写的「去发布」都不算。
- 一定先跑 `--dry`，把结果给用户看，确认后再把 `--dry` 换成 `--go`。
- 同一个文件上传过会记进上传账本，重复上传会被拦下；要重传先问用户，再用 `$YT uploads --forget <文件>`。

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
| `--language <代码>` | 标题简介和音轨的语言，如 `en`、`ja`、`zh-Hans`；不写就用配置的 `publish.language`。要写多语言标题必须先设它 |
| `--audio-language <代码>` | 音轨语言和标题语言不同时单独写；不写就跟 `--language` 一样 |
| `--caption <语言>=<字幕文件>` | 字幕，可以写多次，一种语言一次；支持 srt、vtt、sbv、ttml 等；带名称写成 `"en:English (CC)=字幕.srt"`；每条 400 配额单位 |
| `--ai-disclosure yes\|no` | AI 合成内容声明；不写就用配置的 `publish.aiDisclosure`（null = 不声明）。声明为 yes 后 YouTube 会在视频上标「经过修改或合成的内容」 |
| `--localize <语言>=<文件>` | 多语言标题和简介，可以写多次；文件第一行是标题，其余是简介；不能和 `--language` 同一种语言 |
| `--dossier <档案.md>` | 配置 `publish.requireDossier` 为 true 时必须带：这期的档案，传完存进 `<mem>/videos/<视频ID>.md`，值守回评论时照它说 |

档案写这期的一句话、真实数字和来源、做法、预想问答。只写确认过的东西，值守会照着它回复观众。

标题和简介是频道对外说的话：写之前先运行 `$YT persona` 读人设，口吻、自称、禁区（比如不说收入、不夸大能力）都按人设来。

## AI 合成内容声明

YouTube 的规定：看起来真实的 AI 生成或改动内容（让真人说没说过的话、改真实事件的画面、生成以假乱真的场景、AI 生成的音乐是视频主体）必须声明；明显不真实的动画和图表、AI 只用来写脚本 / 标题 / 封面、调色滤镜、画质修复、克隆自己的声音配音不用声明。

- 试运行时把「AI 合成内容声明」那一行念给用户听；这期用了哪些 AI 素材、要不要声明，拿不准就问用户，不要自己替用户决定。
- 已发布的视频改声明：`$YT disclose <视频ID> --ai yes|no --dry|--go`。

## 多语言（字幕、标题简介、音轨）

- **字幕**和**多语言标题简介**插件能做：上传时带上 `--caption` / `--localize`；已经发布的视频用
  - `$YT captions <视频ID>`：看已有字幕；
  - `$YT caption <视频ID> --caption en=… --dry|--go`：补字幕；
  - `$YT localize <视频ID> --language en --localize ja=… --dry|--go`：设语言、补多语言标题简介（已有的其他语言会保留）。
- **多音轨**（同一个视频带几种语言的配音）YouTube API 不支持。传完后告诉用户：到 YouTube Studio → 该视频 → 语言 → 添加语言 → 上传纯音频文件（时长和视频一致），频道要开通高级功能。
- 视频上传成功后，字幕或多语言标题没设上只算警告，按输出里给的命令补，不要重传视频。
- 写多语言标题简介时每种语言都按人设口吻写，不要逐字机翻；数字和说法以档案为准。

## 2. 试运行

```
$YT upload <成片> --title "…" --description-file … --thumbnail … --dossier … --dry
```

把输出里的频道、标题、隐私设置、定时、封面、文件大小、语言、多语言标题、字幕、AI 合成内容声明列给用户，问一句「确认发布吗？」，然后等。

## 3. 上传

用户确认后，同样的参数把 `--dry` 换成 `--go`。看到视频 ID 和链接才算成功；失败就原样报告错误，不要换参数重试。断网中断的话，再跑一次同样的 `--go` 会从断点续传。

## 4. 收尾

1. 告诉用户视频链接。
2. 更新 `<mem>/now.md` 的「最近发布」（标题、链接、发布时间、带了哪些语言的字幕和标题），「正在做」「下一期」按实际情况改。没写进 `now.md` 的事，值守不会对观众说。
3. 确认 `<mem>/videos/<视频ID>.md` 已经生成；漏了就补：`$YT memory dossier <视频ID> --file <档案.md>`。
