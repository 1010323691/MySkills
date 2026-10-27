// 配置 / 人设 / 共享记忆 / 频道数据（2026-10-27，独立版新增）
//
//   node bili.mjs config [show | path | init | check] [--json]
//   node bili.mjs persona [--json]                  人设提示词（回复、发动态、私信前先读）
//   node bili.mjs memory [status | init | dossier <BV号> --file 档案.md | feedback --message … | log --message …]
//   node bili.mjs stats [--n 10] [--fresh] [--no-videos] [--json]   自己账号的数据：粉丝、总播放、获赞 + 最近投稿的播放 / 评论 / 弹幕
//                                                   （--no-videos 不拉投稿列表，值守 duty.videoStats=false 时用）
import fs from 'node:fs'
import path from 'node:path'
import { config, checkConfig, initConfig, configPath } from '../lib/config.mjs'
import { STATE_DIR, DATA_DIR } from '../lib/paths.mjs'
import { personaPrompt } from '../lib/persona.mjs'
import { createMemory, memoryDirOf, MemoryError } from '../lib/memory.mjs'
import { loadCred } from '../lib/cred.mjs'
import { apiGet } from '../lib/bili-api.mjs'
import { makeHeaders } from '../lib/msgfeed.mjs'

const [cmd, ...rest] = process.argv.slice(2)
const positional = [], flags = new Map()
for (let i = 0; i < rest.length; i++) {
  const a = rest[i]
  if (!a.startsWith('--')) { positional.push(a); continue }
  const n = rest[i + 1]
  flags.set(a.slice(2), n === undefined || n.startsWith('--') ? true : (i++, n))
}
const sub = positional[0]
const JSON_OUT = flags.has('json')
const out = (data, human) => JSON_OUT ? console.log(JSON.stringify(data, null, 2)) : human(data)
const text = k => { const v = flags.get(k); return typeof v === 'string' ? v : undefined }
const cfg = config()

async function stats(n, withVideos = true) {
  const cred = loadCred()
  const H = makeHeaders(cred)
  const nav = await apiGet('https://api.bilibili.com/x/web-interface/nav', H, { noCache: true })
  if (nav.code !== 0 || !nav.data?.isLogin) throw new Error('没登录或凭据失效：运行 bili login')
  const mid = String(cfg.self.mid || nav.data.mid)
  const rel = await apiGet(`https://api.bilibili.com/x/relation/stat?vmid=${mid}`, H, { noCache: true })
  const up = await apiGet(`https://api.bilibili.com/x/space/upstat?mid=${mid}`, H, { noCache: true })
  // 投稿列表：公开的空间接口 arc/search 风控最严（2026-10-27 实测：冷却 5 分钟后第一次调用照样 412，整个 IP 熔断）✗
  //   → 改走创作中心「稿件管理」接口（自己的号看自己的稿件，带登录态），并且最多 6 小时拉一次，其余时候用缓存；
  //     拉失败就用旧缓存并标注，不连累粉丝 / 播放这些轻接口
  const CACHE = path.join(DATA_DIR, 'stats-videos.json'), TTL = 6 * 3600 * 1000
  let cache = null
  try { cache = JSON.parse(fs.readFileSync(CACHE, 'utf8')) } catch {}
  const warnings = [rel, up].filter(x => x.code !== 0).map(x => `code=${x.code} ${x.message ?? ''}`)
  let list = withVideos && cache?.mid === mid ? cache : null
  if (withVideos && (!list || flags.has('fresh') || Date.now() - Date.parse(list.at) > TTL)) {
    try {
      if (String(nav.data.mid) !== mid) throw new Error(`登录的号（mid ${nav.data.mid}）和 self.mid 不一致，创作中心只能看自己的稿件`)
      const q = new URLSearchParams({ status: 'is_pubing,pubed,not_pubed', pn: '1', ps: String(Math.min(20, Math.max(1, n))), coop: '1', interactive: '1' })
      const arc = await apiGet(`https://member.bilibili.com/x/web/archives?${q}`, { ...H, referer: 'https://member.bilibili.com/platform/upload-manager/article' }, { noCache: true })
      if (arc.code !== 0) throw new Error(`code=${arc.code} ${arc.message ?? ''}`)
      const videos = (arc.data?.arc_audits ?? []).map(({ Archive: a = {}, stat: st = {} }) => ({ id: a.bvid, title: a.title ?? '',
        publishedAt: (a.ptime || a.ctime) ? new Date((a.ptime || a.ctime) * 1000).toISOString() : null,
        views: Number(st.view ?? 0), comments: Number(st.reply ?? 0), danmaku: Number(st.danmaku ?? 0), likes: Number(st.like ?? 0) }))
      list = { mid, at: new Date().toISOString(), count: Number(arc.data?.page?.count ?? videos.length), videos }
      fs.mkdirSync(DATA_DIR, { recursive: true })
      fs.writeFileSync(CACHE, JSON.stringify(list, null, 2))
    } catch (e) {
      warnings.push(`投稿列表没取到（${String(e.message).slice(0, 80)}）${list ? `，用的是 ${new Date(list.at).toLocaleString('zh-CN', { hour12: false })} 的缓存` : ''}`)
    }
  }
  const videos = list?.videos ?? []
  const sum = k => videos.reduce((a, v) => a + (Number(v[k]) || 0), 0)
  return {
    at: new Date().toISOString(),
    channel: { id: mid, title: nav.data.uname, subscribers: Number(rel.data?.follower ?? 0), views: Number(up.data?.archive?.view ?? 0),
      likes: Number(up.data?.likes ?? 0), videos: list?.count ?? null },
    // 投稿列表没拉（--no-videos）或拉不到又没缓存：recent 为 null，汇报省略逐个投稿那几行
    recent: list ? { count: videos.length, views: sum('views'), comments: sum('comments'), danmaku: sum('danmaku'), cachedAt: list.at } : null,
    videos,
    warnings,
  }
}

try {
  if (cmd === 'config') {
    if (sub === 'path') console.log(configPath)
    else if (sub === 'init') {
      const r = initConfig()
      console.log(r.created ? `✓ 已从模板生成配置：${r.path}\n  下一步：按 skill bili-setup 填写，再 bili config check` : `配置已经存在，没动它：${r.path}`)
    } else if (sub === 'check') {
      out(checkConfig(), x => {
        console.log(`配置文件：${x.path}${x.exists ? '' : '（不存在）'}`)
        for (const n of x.notes ?? []) console.log('ℹ ' + n)
        if (!x.problems.length) return console.log('✓ 配置没问题')
        for (const p of x.problems) console.log('✗ ' + p)
        process.exitCode = 1
      })
    } else if (!sub || sub === 'show') {
      const { youtube, __hasUserFile, ...shown } = cfg
      out({ path: configPath, stateDir: STATE_DIR, ...shown }, x => console.log(JSON.stringify(x, null, 2)))
    } else throw new Error('config 子命令：show / path / init / check')
  } else if (cmd === 'persona') {
    out(personaPrompt(cfg), x => { if (x.problem) console.error('⚠ ' + x.problem); console.log(x.prompt || '（没有人设）') })
  } else if (cmd === 'memory') {
    const mem = createMemory(memoryDirOf(cfg))
    if (!sub || sub === 'status') out(mem.info(), m => {
      console.log(`共享记忆：${m.dir}${m.ready ? '' : '（还没初始化：bili memory init）'}`)
      console.log(`  视频档案 ${m.videos.length} 期${m.videos.length ? '：' + m.videos.join('、') : ''} · 待处理反馈 ${m.openFeedback} 条`)
    })
    else if (sub === 'init') { const r = mem.init(); console.log(`✓ 已建好 ${r.dir}${r.created.length ? `（新建：${r.created.join('、')}）` : '（文件都在，没动）'}`) }
    else if (sub === 'dossier') {
      const file = text('file')
      if (!file) throw new MemoryError('用法：bili memory dossier <BV号> --file 档案.md', 'MEM_ARGS')
      const p = mem.writeDossier(positional[1], { url: `https://www.bilibili.com/video/${positional[1]}`, body: fs.readFileSync(path.resolve(file), 'utf8') }, { force: flags.has('force') })
      console.log(`✓ 已写入 ${p}`)
    } else if (sub === 'feedback') {
      console.log('✓ 已记进反馈池：' + mem.appendFeedback({ videoId: text('video') ?? '', commentId: text('comment-id') ?? '', author: text('who') ?? '', kind: text('kind') ?? '其他', message: text('message') ?? '' }))
    } else if (sub === 'log') {
      console.log('✓ 已记进值守日志：' + mem.appendJournal({ message: `[B站] ${text('message') ?? ''}` }))
    } else throw new Error('memory 子命令：status / init / dossier / feedback / log')
  } else if (cmd === 'stats') {
    const r = await stats(Number(text('n')) || 10, !flags.has('no-videos'))
    out(r, x => {
      const c = x.channel
      console.log(`${c.title}：粉丝 ${c.subscribers} · 总播放 ${c.views} · 获赞 ${c.likes}${c.videos == null ? '' : ` · 投稿 ${c.videos} 个`}`)
      if (x.recent) console.log(`最近 ${x.recent.count} 个投稿合计：播放 ${x.recent.views} · 评论 ${x.recent.comments} · 弹幕 ${x.recent.danmaku}${x.recent.cachedAt ? `（投稿数据 ${new Date(x.recent.cachedAt).toLocaleString('zh-CN', { hour12: false }).slice(5, -3)} 更新，6 小时刷新一次）` : ""}`)
      for (const v of x.videos) console.log(`  ${v.id}  ${v.publishedAt?.slice(0, 10) ?? ''}  播放 ${v.views} · 评论 ${v.comments} · 弹幕 ${v.danmaku}  ${v.title.slice(0, 40)}`)
      for (const w of x.warnings) console.log('  ⚠ 部分数据没取到：' + w)
    })
  } else throw new Error(`未知子命令：${cmd}`)
} catch (e) {
  console.error('✗ ' + e.message)
  process.exit(e instanceof MemoryError && e.code !== 'MEM' ? 2 : 1)
}
