#!/usr/bin/env node
// YouTube（阶段 1）：登录 + 看自己频道视频的评论区 + 回复评论
//
//   yt auth client <下载的客户端.json>   # 一次性：导入 Google Cloud 的 OAuth 客户端（--stdin 从管道读）
//   yt auth login [--no-open]            # 浏览器授权（回环地址 + PKCE）
//   yt auth status | logout
//   yt videos [--n 10]                   # 自己频道最近的视频
//   yt persona                           # 人设提示词（配置 persona 段 + 人设文件），回复前先读
//   yt stats [--n 10]                    # 频道数据：订阅、总播放、视频数 + 最近视频的播放 / 评论 / 赞
//   yt comments <视频ID> [--n 20] [--order time|relevance]
//   yt inbox [--n 20] [--unreplied]      # 整个频道的评论收件箱
//   yt thread <楼ID>                     # 一整条楼（回复后回读核查用）
//   yt reply <评论ID> --message "…" --dry|--go
//   yt replied [--forget <评论ID>]       # 判重账本
//   yt upload <视频文件> --title "…" [--description "…"] [--privacy public] --dry|--go   # 只在主人下指令时用
//   yt uploads [--forget <视频文件>]      # 上传账本
//   yt captions <视频ID>                 # 视频已有的字幕
//   yt disclose <视频ID> --ai yes|no --dry|--go   # 设 AI 合成内容声明
//   yt caption <视频ID> --caption en=字幕.srt [--caption ja=…] --dry|--go   # 给已发布的视频补字幕
//   yt localize <视频ID> [--language en] [--audio-language en] [--localize ja=标题简介.txt …] --dry|--go   # 设语言、补多语言标题简介
//   yt config [show | path | init | check]             # 配置文件（模板见 config.template.json，skill yt-setup 引导填写）
//   yt memory [init | dossier <视频ID> [--file 档案.md] | feedback --message "…" | log --message "…"]   # 频道共享记忆
//
// 所有读命令都可加 --json。写操作是 reply、upload、caption、localize，必须显式 --dry（只打印请求）或 --go（真的发）。
import fs from 'node:fs'
import path from 'node:path'
import { spawn, spawnSync } from 'node:child_process'
import { config, dataPath, checkConfig, initConfig, configPath } from '../lib/config.mjs'
import { createYouTube, youtubeSettings, YouTubeError } from '../lib/youtube.mjs'
import { createMemory, memoryDirOf, MemoryError } from '../lib/memory.mjs'
import { personaPrompt } from '../lib/persona.mjs'

const fullCfg = config()
const cfg = fullCfg.youtube ?? {}
const memoryDir = memoryDirOf(fullCfg)
const memory = () => createMemory(memoryDir)

// 代理：Node 自带的 fetch 默认不读 HTTPS_PROXY；Node 22.21+/24 设 NODE_USE_ENV_PROXY=1 才走代理 → 带上环境变量重启自己一次
const proxy = String(cfg.proxy ?? '').trim() || process.env.HTTPS_PROXY || process.env.https_proxy || ''
if (proxy && process.env.NODE_USE_ENV_PROXY !== '1') {
  const r = spawnSync(process.execPath, process.argv.slice(1), { stdio: 'inherit', env: { ...process.env, HTTPS_PROXY: proxy, HTTP_PROXY: proxy, NODE_USE_ENV_PROXY: '1' } })
  process.exit(r.status ?? 1)
}

const positional = [], flags = new Map(), multi = new Map()
for (let i = 2; i < process.argv.length; i += 1) {
  const a = process.argv[i]
  if (!a.startsWith('--')) { positional.push(a); continue }
  const next = process.argv[i + 1]
  const v = next === undefined || next.startsWith('--') ? true : (i += 1, next)
  flags.set(a.slice(2), v)
  // --caption / --localize 可以写多次：每次都收进 multi
  if (!multi.has(a.slice(2))) multi.set(a.slice(2), [])
  multi.get(a.slice(2)).push(v)
}
const many = key => (multi.get(key) ?? []).filter(v => typeof v === 'string')
// --caption en=字幕.srt，或带名称 --caption "en:English (CC)=字幕.srt"
const captionArgs = () => many('caption').map(v => {
  const i = v.indexOf('=')
  if (i < 1) throw new YouTubeError(`--caption 要写成 语言=字幕文件，例如 en=subs/en.srt：${v}`, 'YT_ARGS')
  const head = v.slice(0, i), j = head.indexOf(':')
  return { lang: (j < 0 ? head : head.slice(0, j)).trim(), name: j < 0 ? '' : head.slice(j + 1).trim(), file: v.slice(i + 1).trim(), draft: flags.has('caption-draft') }
})
// --localize ja=标题简介.txt：文件第一行是标题，空一行之后是简介
const localizeArgs = () => many('localize').map(v => {
  const i = v.indexOf('=')
  if (i < 1) throw new YouTubeError(`--localize 要写成 语言=文件，例如 ja=meta/ja.txt：${v}`, 'YT_ARGS')
  const file = path.resolve(v.slice(i + 1).trim())
  let text
  try { text = fs.readFileSync(file, 'utf8').replace(/^﻿/, '').replace(/\r\n/g, '\n') } catch { throw new YouTubeError(`找不到多语言标题文件：${file}`, 'YT_ARGS') }
  const lines = text.split('\n'), k = lines.findIndex(l => l.trim())
  return { lang: v.slice(0, i).trim(), title: k < 0 ? '' : lines[k].trim(), description: k < 0 ? '' : lines.slice(k + 1).join('\n').trim() }
})
const langLabel = l => { try { return `${l}（${new Intl.DisplayNames(['zh-CN'], { type: 'language' }).of(l)}）` } catch { return l } }
const [cmd, sub] = positional
const JSON_OUT = flags.has('json')
const text0 = key => { const v = flags.get(key); return typeof v === 'string' ? v : undefined }
const num = (key, fallback) => { const n = Number(flags.get(key)); return Number.isFinite(n) && n > 0 ? Math.floor(n) : fallback }

const yt = createYouTube({ directory: fullCfg.dataDir, settings: () => youtubeSettings(cfg) })

function usage(code = 0) {
  console.log(fs.readFileSync(new URL(import.meta.url), 'utf8').split('\n').slice(1, 22).map(l => l.replace(/^\/\/ ?/, '')).join('\n'))
  console.log('上传的其余参数：--description-file <文件> --tags a,b --category 22 --privacy public|unlisted|private\n' +
    '              --publish-at 2026-11-01T20:00:00+08:00（定时发布，自动先私享）--kids（面向儿童）--thumbnail 封面.jpg --playlist PLxxxx\n' +
    '              --dossier 档案.md（这期的构想 / 要点 / 预想问答，传完存进共享记忆 videos/<视频ID>.md）\n' +
    '多语言参数：--language en（标题简介和音轨的语言）--audio-language en（音轨语言不同时单独写）\n' +
    '              --caption en=字幕.srt（可写多次；带名称写成 "en:English (CC)=字幕.srt"；--caption-draft 存为草稿）\n' +
    '              --localize ja=标题简介.txt（可写多次；文件第一行是标题，其余是简介）\n' +
    '              多音轨：YouTube API 不支持，只能在 Studio → 语言 里手动加\n' +
    'AI 声明：--ai-disclosure yes|no（看起来真实的 AI 生成 / 改动内容要声明；动画、AI 写脚本、克隆自己的声音不用）\n' +
    '反馈参数：yt memory feedback --message "一句话概括" [--kind 提问|想看|纠错|批评|建议|其他] [--video <视频ID>] [--comment-id <评论ID>] [--who <昵称>]')
  process.exit(code)
}
const mb = n => (n / 1024 / 1024).toFixed(1) + ' MB'
function openBrowser(url) {
  const [file, args] = process.platform === 'win32' ? ['rundll32', ['url.dll,FileProtocolHandler', url]]
    : process.platform === 'darwin' ? ['open', [url]] : ['xdg-open', [url]]
  try { spawn(file, args, { detached: true, stdio: 'ignore', windowsHide: true }).on('error', () => {}).unref() } catch {}
}
const short = (s, n = 120) => { const t = String(s ?? '').replace(/\s+/g, ' ').trim(); return [...t].length > n ? [...t].slice(0, n).join('') + '…' : t }
function printThread(t) {
  const flag = t.mine ? '（我）' : t.repliedByMe ? '（已回）' : ''
  console.log(`● ${t.author}${flag} · ${t.publishedAt?.slice(0, 16).replace('T', ' ') ?? ''} · 赞 ${t.likes} · 回复 ${t.replyCount}${t.canReply ? '' : ' · 不可回复'}`)
  console.log(`  ${short(t.text, 300)}`)
  console.log(`  评论ID=${t.id}${t.videoId ? '  视频=' + t.videoId : ''}`)
  for (const r of t.replies ?? []) console.log(`    ↳ ${r.author}${r.mine ? '（我）' : ''}：${short(r.text)}  [评论ID=${r.id}]`)
}
const out = (data, human) => { if (JSON_OUT) console.log(JSON.stringify(data, null, 2)); else human(data) }

async function main() {
  if (!cmd || cmd === 'help' || flags.has('help')) usage(cmd ? 0 : 2)

  if (cmd === 'auth') {
    if (sub === 'client') {
      const file = positional[2]
      // --stdin：设置页用（内容经管道传进来，不落临时文件 ✓）
      if (!file && !flags.has('stdin')) throw new YouTubeError('用法：yt auth client <从 Google Cloud 下载的客户端 JSON>', 'YT_ARGS')
      const raw = flags.has('stdin') ? fs.readFileSync(0, 'utf8') : fs.readFileSync(path.resolve(file), 'utf8')
      const r = yt.saveClient(raw)
      console.log(`✓ 已导入 OAuth 客户端（${r.client_id.slice(0, 12)}…）。下一步：yt auth login`)
      console.log('  原文件里有 client_secret，导入后可以删掉下载的那份 ✓')
      return
    }
    if (sub === 'login') {
      const channel = await yt.login({ open: url => {
        console.log('在浏览器里打开下面的地址，用要给插件用的那个 Google 账号登录并同意：\n')
        console.log(url + '\n')
        console.log('（等你授权，最多 5 分钟…）')
        if (!flags.has('no-open')) openBrowser(url)
      } })
      console.log(`✓ 已登录 YouTube 频道：${channel.title}${channel.handle ? ' ' + channel.handle : ''}（${channel.id}）`)
      return
    }
    if (sub === 'logout') { const r = await yt.logout(); console.log(r.removed ? `✓ 已退出${r.revoked ? '，Google 侧授权已撤销' : '（Google 侧撤销没成功，可到 https://myaccount.google.com/permissions 手动移除）'}` : '本来就没登录'); return }
    if (sub === 'status' || !sub) {
      const mem = memoryDir ? memory().info() : null
      return out({ ...yt.status(), memory: mem }, s => {
        console.log(`OAuth 客户端：${s.client ? '✓ 已导入' : '✗ 未导入（yt auth client <文件>）'}`)
        console.log(`登录：${s.loggedIn ? `✓ ${s.channel?.title ?? ''}（${s.channel?.id ?? '?'}）` : '✗ 未登录（yt auth login）'}`)
        console.log(`今日配额（太平洋时间 ${s.quota.day}）：${s.quota.units}/${s.quota.dailyUnits} 单位 · 回复 ${s.quota.writes}/${s.quota.writeDaily} 条 · 上传 ${s.quota.uploads}/${s.quota.uploadDaily} 个`)
        if (s.pausedUntil) console.log(`⚠ 已暂停到 ${s.pausedUntil}：${s.pauseReason}`)
        console.log(`共享记忆：${mem ? `${mem.dir}${mem.ready ? ` · 档案 ${mem.videos.length} 期 · 待处理反馈 ${mem.openFeedback} 条` : ' · ✗ 还没初始化（yt memory init）'}` : '未设置（配置里的 memoryDir）'}`)
      })
    }
    throw new YouTubeError('auth 子命令：client / login / status / logout', 'YT_ARGS')
  }

  if (cmd === 'me') return out(await yt.me({ fresh: flags.has('fresh') }), c => console.log(`${c.title}${c.handle ? ' ' + c.handle : ''} · 频道ID=${c.id}`))

  if (cmd === 'videos') {
    return out(await yt.myVideos({ n: num('n', 10) }), list => {
      if (!list.length) return console.log('（频道里还没有视频）')
      for (const v of list) console.log(`${v.id}  ${v.publishedAt?.slice(0, 10) ?? ''}  评论 ${v.comments ?? '关闭'} · 播放 ${v.views}  ${short(v.title, 60)}`)
    })
  }

  if (cmd === 'persona') {
    // 人设提示词：配置的 persona 段 + 人设文件全文；回复评论、写简介前先读
    const p = personaPrompt(fullCfg)
    return out(p, x => {
      if (x.problem) console.error('⚠ ' + x.problem)
      console.log(x.prompt || '（没有人设）')
    })
  }

  if (cmd === 'stats') {
    return out(await yt.stats({ n: num('n', 10) }), x => {
      const c = x.channel
      console.log(`${c.title}：订阅 ${c.subscribers ?? '（已隐藏）'} · 总播放 ${c.views} · 视频 ${c.videos} 个`)
      console.log(`最近 ${x.recent.count} 个视频合计：播放 ${x.recent.views} · 评论 ${x.recent.comments} · 赞 ${x.recent.likes}`)
      for (const v of x.videos) console.log(`  ${v.id}  ${v.publishedAt?.slice(0, 10) ?? ''}  播放 ${v.views} · 评论 ${v.comments ?? '关闭'} · 赞 ${v.likes ?? '隐藏'}  ${short(v.title, 50)}`)
    })
  }

  if (cmd === 'comments') {
    const r = await yt.comments(sub, { n: num('n', 20), order: flags.get('order') })
    return out(r, x => {
      console.log(`《${x.video.title}》 ${x.threads.length} 条楼\n`)
      for (const t of x.threads) { printThread(t); console.log() }
    })
  }

  if (cmd === 'inbox') {
    const list = await yt.inbox({ n: num('n', 20), unreplied: flags.has('unreplied') })
    return out(list, l => {
      if (!l.length) return console.log(flags.has('unreplied') ? '（没有待回的评论）' : '（还没有评论）')
      for (const t of l) { printThread(t); console.log() }
      if (flags.has('unreplied')) console.log('注：「待回」按每条楼附带的最近几条回复判断，楼很长时以 yt thread 为准')
    })
  }

  if (cmd === 'thread') {
    return out(await yt.thread(sub), t => printThread(t))
  }

  if (cmd === 'reply') {
    const go = flags.has('go'), dry = flags.has('dry')
    if (go === dry) throw new YouTubeError('写操作必须二选一：--dry（只打印请求）或 --go（真的发）', 'YT_ARGS')
    const message = flags.get('message')
    if (typeof message !== 'string') throw new YouTubeError('用法：yt reply <评论ID> --message "回复内容" --dry|--go', 'YT_ARGS')
    const r = await yt.reply(sub, message, { go })
    if (!r.dry) {
      try {
        fs.appendFileSync(dataPath('activity.jsonl'), JSON.stringify({ at: new Date().toISOString(), kind: 'yt-reply-sent', target: r.target.author,
          note: `YouTube 回复 · 视频 ${r.videoId} · ${short(r.text, 60)}` }) + '\n')
      } catch {}
      // 记进共享记忆：工作室那边据此知道频道在评论区公开说过什么 ✓
      if (memoryDir) try { memory().logReply({ videoId: r.videoId, commentId: r.commentId, author: r.target.author, comment: r.target.text, reply: r.text }) } catch {}
    }
    return out(r, x => {
      console.log(`回复对象：${x.target.author}：${short(x.target.text)}`)
      console.log(`视频：${x.videoId} · 楼ID：${x.threadId}`)
      if (x.commentId !== x.threadId && !/^@/.test(String(message).trim())) console.log('提示：这是楼中楼回复，YouTube 只有两层；想让对方收到提醒，正文开头写 @对方名字')
      if (x.dry) {
        console.log('\n[dry] 将发送：')
        console.log(JSON.stringify(x.request, null, 2))
        console.log('\n确认无误后把 --dry 换成 --go')
      } else {
        console.log(`\n✓ 已回复 回复ID=${x.replyId}`)
        console.log(`  回读核查：yt thread ${x.threadId}`)
      }
    })
  }

  if (cmd === 'captions') {
    return out(await yt.listCaptions(sub), list => {
      if (!list.length) return console.log('（这个视频还没有字幕）')
      for (const c of list) console.log(`${langLabel(c.lang)}「${c.name}」${c.kind === 'asr' ? ' · 自动生成' : ''}${c.draft ? ' · 草稿' : ''} · ${c.status ?? ''}  ID=${c.id}`)
    })
  }

  if (cmd === 'caption') {
    const go = flags.has('go'), dry = flags.has('dry')
    if (go === dry) throw new YouTubeError('写操作必须二选一：--dry（只看要传什么）或 --go（真的传）', 'YT_ARGS')
    const r = await yt.addCaptions(sub, captionArgs(), { go })
    return out(r, x => {
      console.log(`视频：${x.title}（${x.videoId}）`)
      if (x.dry) {
        for (const c of x.captions) console.log(`  [dry] 字幕 ${langLabel(c.lang)}「${c.name}」：${c.file}${c.draft ? ' · 草稿' : ''}`)
        console.log(`  要花 ${x.units} 配额单位。确认无误后把 --dry 换成 --go`)
      } else {
        for (const c of x.done) console.log(`  ✓ 字幕 ${langLabel(c.lang)}「${c.name}」`)
        for (const c of x.failed) console.log(`  ✗ 字幕 ${langLabel(c.lang)}「${c.name}」：${c.error}`)
        if (x.failed.length) process.exitCode = 1
      }
    })
  }

  if (cmd === 'localize') {
    const go = flags.has('go'), dry = flags.has('dry')
    if (go === dry) throw new YouTubeError('写操作必须二选一：--dry（只看要改什么）或 --go（真的改）', 'YT_ARGS')
    const r = await yt.localize(sub, { language: text0('language'), audioLanguage: text0('audio-language'), localizations: localizeArgs() }, { go })
    return out(r, x => {
      console.log(`视频：${x.title}（${x.videoId}）`)
      console.log(`  ${x.dry ? '[dry] ' : '✓ '}默认语言 ${x.defaultLanguage ? langLabel(x.defaultLanguage) : '（未设）'} · 音轨 ${x.audioLanguage ? langLabel(x.audioLanguage) : '（未设）'}`)
      if (x.adding.length) console.log(`  ${x.dry ? '[dry] 将写入' : '✓ 已写入'}多语言标题简介：${x.adding.map(langLabel).join('、')}`)
      if (x.keeping.length) console.log(`  保留已有：${x.keeping.map(langLabel).join('、')}`)
      if (x.dry) console.log('  要花 50 配额单位。确认无误后把 --dry 换成 --go')
    })
  }

  if (cmd === 'disclose') {
    const go = flags.has('go'), dry = flags.has('dry')
    if (go === dry) throw new YouTubeError('写操作必须二选一：--dry（只看要改什么）或 --go（真的改）', 'YT_ARGS')
    const r = await yt.disclose(sub, { ai: text0('ai') }, { go })
    return out(r, x => {
      const yn = b => b ? '是' : '否'
      console.log(`视频：${x.title}（${x.videoId}）`)
      if (!x.changed) return console.log(`  AI 合成内容声明已经是「${yn(x.after)}」，不用改`)
      console.log(`  ${x.dry ? '[dry] ' : '✓ '}AI 合成内容声明：${yn(x.before)} → ${yn(x.after)}`)
      if (x.dry) console.log('  要花 50 配额单位。确认无误后把 --dry 换成 --go')
    })
  }

  if (cmd === 'upload') {
    const go = flags.has('go'), dry = flags.has('dry')
    if (go === dry) throw new YouTubeError('上传必须二选一：--dry（只看要发什么）或 --go（真的传）', 'YT_ARGS')
    if (!sub) throw new YouTubeError('用法：yt upload <视频文件> --title "标题" --dry|--go', 'YT_ARGS')
    const text = key => { const v = flags.get(key); return typeof v === 'string' ? v : undefined }
    const descFile = text('description-file')
    // 档案先读进来再传：文件不对就在上传前报错，别等视频发出去了才发现 ✓
    const dossierFile = text('dossier')
    if (flags.has('dossier') && !dossierFile) throw new YouTubeError('--dossier 后面要跟档案文件路径', 'YT_ARGS')
    if (dossierFile && !memoryDir) throw new YouTubeError('还没设置共享记忆目录（配置里的 memoryDir），--dossier 没地方存', 'YT_ARGS')
    let dossier = null
    if (dossierFile) { try { dossier = fs.readFileSync(path.resolve(dossierFile), 'utf8') } catch { throw new YouTubeError(`找不到档案文件：${dossierFile}`, 'YT_ARGS') } }
    if (!dossierFile && fullCfg.publish.requireDossier && memoryDir) throw new YouTubeError('配置要求每期都带档案（publish.requireDossier）：加上 --dossier <档案.md>', 'YT_ARGS')
    if (dossier !== null && !dossier.trim()) throw new YouTubeError('档案文件是空的', 'YT_ARGS')
    const input = {
      file: sub, title: text('title'), description: descFile ? fs.readFileSync(path.resolve(descFile), 'utf8') : text('description'),
      tags: text('tags') ?? (fullCfg.publish.tags?.length ? fullCfg.publish.tags.join(',') : undefined),
      category: text('category') ?? (fullCfg.publish.category || undefined),
      // 定时发布必须私享 → 有 --publish-at 时不套默认隐私
      privacy: text('privacy') ?? (text('publish-at') ? undefined : fullCfg.publish.privacy), publishAt: text('publish-at'),
      kids: flags.has('kids'), thumbnail: text('thumbnail'), playlist: text('playlist') ?? (fullCfg.publish.playlist || undefined),
      language: text('language') ?? (fullCfg.publish.language || undefined),
      audioLanguage: text('audio-language') ?? (fullCfg.publish.audioLanguage || undefined),
      captions: captionArgs(), localizations: localizeArgs(),
      // AI 合成内容声明：--ai-disclosure yes|no；不写就用配置 publish.aiDisclosure（null = 不声明，YouTube 默认）
      aiDisclosure: text('ai-disclosure') ?? fullCfg.publish.aiDisclosure ?? undefined,
    }
    let last = 0
    const r = await yt.upload(input, { go, onProgress: (done, total) => {
      if (done === total || Date.now() - last > 2000) { last = Date.now(); process.stderr.write(`  上传中 ${mb(done)} / ${mb(total)}（${Math.floor(done / total * 100)}%）\n`) }
    } })
    if (!r.dry) {
      try {
        fs.appendFileSync(dataPath('activity.jsonl'), JSON.stringify({ at: new Date().toISOString(), kind: 'yt-upload', target: r.videoId,
          note: `YouTube 上传 · ${r.privacy} · ${short(r.title, 60)}` }) + '\n')
      } catch {}
      if (dossier) {
        try { r.dossier = memory().writeDossier(r.videoId, { title: r.title, url: r.url, publishedAt: r.publishAt || new Date().toISOString(), body: dossier }) }
        catch (e) { r.warnings.push(`档案没存上：${e.message}（之后补：yt memory dossier ${r.videoId} --file "${dossierFile}"）`) }
      }
    }
    return out(r, x => {
      if (x.dry) {
        const s = x.status
        console.log(`[dry] 将上传到频道：${x.channel}`)
        console.log(`  文件：${x.file}（${mb(x.size)}）${x.resume ? ' · 有未完成的上传，--go 时从断点接着传' : ''}`)
        console.log(`  标题：${x.snippet.title}`)
        console.log(`  简介：${x.snippet.description ? short(x.snippet.description, 80) : '（空）'}`)
        console.log(`  标签：${x.snippet.tags.join('，') || '（无）'} · 分类 ${x.snippet.categoryId}`)
        console.log(`  可见性：${{ public: '公开', unlisted: '不公开（有链接可看）', private: '私享' }[s.privacyStatus]}${s.publishAt ? ` · 定时 ${s.publishAt} 自动公开` : ''}`)
        console.log(`  面向儿童：${s.selfDeclaredMadeForKids ? '是' : '否'}`)
        if (x.thumbnail) console.log(`  封面：${x.thumbnail}`)
        if (x.playlistId) console.log(`  加入播放列表：${x.playlistId}`)
        console.log(`  语言：标题简介 ${x.snippet.defaultLanguage ? langLabel(x.snippet.defaultLanguage) : '（未设）'} · 音轨 ${x.snippet.defaultAudioLanguage ? langLabel(x.snippet.defaultAudioLanguage) : '（未设）'}`)
        for (const [l, v] of Object.entries(x.localizations ?? {})) console.log(`  多语言标题 ${langLabel(l)}：${short(v.title, 60)}${v.description ? ' · 简介 ' + short(v.description, 30) : ''}`)
        for (const c of x.captions ?? []) console.log(`  字幕 ${langLabel(c.lang)}「${c.name}」：${c.file}（${(c.size / 1024).toFixed(1)} KB）${c.draft ? ' · 草稿' : ''}`)
        if (x.captions?.length) console.log(`  字幕要花 ${x.captions.length * 400} 配额单位`)
        console.log(`  AI 合成内容声明：${s.containsSyntheticMedia === true ? '是（YouTube 会在视频上标「经过修改或合成的内容」）' : s.containsSyntheticMedia === false ? '否' : '未声明（YouTube 默认按否处理）'}`)
        console.log('  多音轨：YouTube API 不支持，传完到 Studio → 语言 里手动添加')
        if (dossier) console.log(`  档案：${path.resolve(dossierFile)} → 传完存进 ${path.join(memoryDir, 'videos')}`)
        console.log('\n确认无误后把 --dry 换成 --go')
      } else {
        console.log(`\n✓ 已上传 视频ID=${x.videoId}`)
        console.log(`  ${x.url} · ${{ public: '公开', unlisted: '不公开', private: '私享' }[x.privacy] ?? x.privacy}${x.publishAt ? ` · 定时 ${x.publishAt}` : ''}`)
        console.log('  YouTube 还要转码几分钟，刚传完可能暂时看不了')
        if (x.dossier) console.log(`  档案：${x.dossier}`)
        if (x.aiDisclosure !== null) console.log(`  AI 合成内容声明：${x.aiDisclosure ? '是' : '否'}`)
        if (x.language) console.log(`  语言：${langLabel(x.language)}${x.audioLanguage && x.audioLanguage !== x.language ? ' · 音轨 ' + langLabel(x.audioLanguage) : ''}`)
        if (x.localizations.length) console.log(`  多语言标题：${x.localizations.map(langLabel).join('、')}`)
        for (const c of x.captions) console.log(`  ✓ 字幕 ${langLabel(c.lang)}「${c.name}」`)
        for (const w of x.warnings) console.log('  ⚠ ' + w)
      }
    })
  }

  if (cmd === 'uploads') {
    const target = flags.get('forget')
    if (typeof target === 'string') {
      const n = await yt.forgetUpload(target)
      console.log(n ? `✓ 已清掉 ${target} 的未完成 / 不确定记录（确认 YouTube Studio 里没有这条才这么做）` : '账本里没有这个文件的未完成记录（传成功的不能清）')
      return
    }
    return out(yt.uploads(), o => {
      const rows = Object.values(o.byFile ?? {})
      if (!rows.length) return console.log('（还没上传过视频）')
      for (const v of rows) console.log(`${v.at}  ${String(v.status).padEnd(9)}  ${short(v.title, 40)}${v.videoId ? '  → https://youtu.be/' + v.videoId : ''}\n    ${v.file}`)
    })
  }

  if (cmd === 'config') {
    if (sub === 'path') return console.log(configPath)
    if (sub === 'init') {
      const r = initConfig()
      console.log(r.created ? `✓ 已从模板生成配置：${r.path}
  下一步：按 skill yt-setup 填写，再 yt config check` : `配置已经存在，没动它：${r.path}`)
      return
    }
    if (sub === 'check') {
      const r = checkConfig()
      return out(r, x => {
        console.log(`配置文件：${x.path}${x.exists ? '' : '（不存在）'}`)
        if (!x.problems.length) return console.log('✓ 配置没问题')
        for (const p of x.problems) console.log('✗ ' + p)
        process.exitCode = 1
      })
    }
    if (!sub || sub === 'show') {
      const { youtube, ...shown } = fullCfg
      return out({ path: configPath, ...shown }, x => console.log(JSON.stringify(x, null, 2)))
    }
    throw new YouTubeError('config 子命令：show / path / init / check', 'YT_ARGS')
  }

  if (cmd === 'memory') {
    const mem = memory()
    if (!sub || sub === 'status') {
      return out(mem.info(), m => {
        console.log(`共享记忆：${m.dir}${m.ready ? '' : '（还没初始化：yt memory init）'}`)
        console.log(`  视频档案 ${m.videos.length} 期${m.videos.length ? '：' + m.videos.join('、') : ''} · 待处理反馈 ${m.openFeedback} 条`)
      })
    }
    if (sub === 'init') {
      const r = mem.init()
      return out(r, x => console.log(x.created.length ? `✓ 已建好 ${x.dir}（新建：${x.created.join('、')}）` : `✓ ${x.dir} 已经是完整的，什么都没动`))
    }
    if (sub === 'dossier') {
      const id = positional[2]
      const file = flags.get('file')
      if (typeof file === 'string') {
        let body
        try { body = fs.readFileSync(path.resolve(file), 'utf8') } catch { throw new MemoryError(`找不到档案文件：${file}`, 'MEM_ARGS') }
        const known = Object.values(yt.uploads().byFile ?? {}).find(v => v.videoId === id)
        let at
        try { at = mem.writeDossier(id, { title: known?.title, publishedAt: known?.at, body }, { force: flags.has('force') }) }
        catch (e) { if (e.code === 'EEXIST') throw new MemoryError(`这期已经有档案了：${mem.dossierPath(id)}（要覆盖加 --force，或直接编辑那个文件）`, 'MEM_ARGS'); throw e }
        return out({ path: at }, x => console.log(`✓ 已写入 ${x.path}`))
      }
      const text = mem.readDossier(id)
      return out({ path: mem.dossierPath(id), text }, x => console.log(x.text === null ? `（这期还没有档案：${x.path}）` : `${x.path}\n\n${x.text}`))
    }
    if (sub === 'feedback') {
      const s = key => { const v = flags.get(key); return typeof v === 'string' ? v : '' }
      const line = mem.appendFeedback({ videoId: s('video'), commentId: s('comment-id'), author: s('who'), kind: s('kind') || '其他', message: s('message') })
      return out({ line }, x => console.log(`✓ 已记进反馈池：${x.line}`))
    }
    if (sub === 'log') {
      const v = flags.get('message')
      const line = mem.appendJournal({ message: typeof v === 'string' ? v : '' })
      return out({ line }, x => console.log(`✓ 已记进值守日志：${x.line}`))
    }
    throw new YouTubeError('memory 子命令：status / init / dossier <视频ID> [--file 档案.md] / feedback --message "…" / log --message "…"', 'YT_ARGS')
  }

  if (cmd === 'replied') {
    const target = flags.get('forget')
    if (typeof target === 'string') {
      const had = await yt.forget(target)
      console.log(had ? `✓ 已从判重账本移除 ${target}（确认过没发出去才这么做）` : '账本里没有这条')
      return
    }
    return out(yt.replied(), o => {
      const rows = Object.entries(o.byComment ?? {})
      if (!rows.length) return console.log('（还没回过任何评论）')
      for (const [id, v] of rows) console.log(`${v.at}  ${v.status.padEnd(7)}  ${id}${v.replyId ? '  → ' + v.replyId : ''}`)
    })
  }

  throw new YouTubeError(`未知子命令：${cmd}（运行 yt help）`, 'YT_ARGS')
}

main().catch(e => {
  console.error('✗ ' + (e instanceof YouTubeError || e instanceof MemoryError ? e.message : String(e?.stack ?? e)))
  process.exit(['YT_ARGS', 'MEM_ARGS', 'MEM_OFF'].includes(e?.code) ? 2 : 1)
})
