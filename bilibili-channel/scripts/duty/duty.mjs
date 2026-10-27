#!/usr/bin/env node
// B站 值守的巡视器：给 Claude Code 里常驻的值守会话用，配合 skill `bili-duty`
//
//   node scripts/duty/duty.mjs check          # 拉「回复我的」+「@我的」，和上一轮比 → 打印 JSON：这一轮要不要干活、干什么
//   node scripts/duty/duty.mjs done [--diary] # 这一轮做完了：记下看过的消息（--diary 记下今天已写值守日志）
//
// 它只读、只记状态，不发评论；回复走 `bili comment … --go`（限额、判重、回读都在那边）
// 状态文件：<共享记忆目录>/.bili-duty-state.json；没设共享记忆就放 <数据目录>/state/duty-state.json
// 参数全部来自配置文件的 duty / risk 段（bili config show 可看），这里不写死
import fs from 'node:fs'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { config, checkConfig } from '../bili/lib/config.mjs'
import { dshPath } from '../bili/lib/paths.mjs'
import { memoryDirOf } from '../bili/lib/memory.mjs'
import { personaPrompt } from '../bili/lib/persona.mjs'
import { loadCred } from '../bili/lib/cred.mjs'
import { makeHeaders, pullFeed, resolveLatestReply } from '../bili/lib/msgfeed.mjs'

const BILI = fileURLToPath(new URL('../bili/bili.mjs', import.meta.url))
const cfg = config()
const D = cfg.duty
const memDir = memoryDirOf(cfg)
const STATE = memDir ? path.join(memDir, '.bili-duty-state.json') : dshPath('duty-state.json')

const today = () => new Date().toLocaleDateString('sv-SE')
const hhmm = ms => new Date(ms).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
const load = () => { try { return JSON.parse(fs.readFileSync(STATE, 'utf8')) } catch { return {} } }
const save = s => { fs.mkdirSync(path.dirname(STATE), { recursive: true }); fs.writeFileSync(STATE, JSON.stringify(s, null, 2)) }
const bili = (...args) => {
  const r = spawnSync(process.execPath, [BILI, ...args, '--json'], { encoding: 'utf8', timeout: 120000 })
  if (r.status !== 0) throw new Error((r.stderr || r.stdout || `bili ${args[0]} 失败`).trim().slice(0, 500))
  return JSON.parse(r.stdout)
}

/** 今天自主发言（带 --auto、不算分享）了几条：读限额闸的账本 quota.json；读不到就当 0 */
function writesToday() {
  try {
    const q = JSON.parse(fs.readFileSync(path.join(cfg.dataDir, 'quota.json'), 'utf8'))
    const day = today()
    return (q.log ?? []).filter(x => x.auto && !x.share && new Date(x.at).toLocaleDateString('sv-SE') === day).length
  } catch { return 0 }
}

const s = load()
const cmd = process.argv[2]

/** 频道数据：失败不影响巡视；和上一轮比出变化 */
function statsWithDelta() {
  let cur
  try { cur = bili('stats', '--n', '10') } catch (e) { return { error: String(e.message).slice(0, 200) } }
  const prev = s.lastStats
  const d = (a, b) => (prev && Number.isFinite(a) && Number.isFinite(b)) ? a - b : null
  const pv = new Map((prev?.videos ?? []).map(v => [v.id, v]))
  const out = {
    since: prev?.at ?? null,
    channel: { ...cur.channel, delta: { subscribers: d(cur.channel.subscribers, prev?.channel?.subscribers), views: d(cur.channel.views, prev?.channel?.views), likes: d(cur.channel.likes, prev?.channel?.likes) } },
    recent: { ...cur.recent },
    videos: cur.videos.map(v => { const p = pv.get(v.id); return { ...v, delta: p ? { views: v.views - p.views, comments: v.comments - p.comments, danmaku: v.danmaku - p.danmaku } : null } }),
    warnings: cur.warnings,
  }
  s.lastStats = cur
  return out
}

if (cmd === 'check') {
  let cred
  try { cred = loadCred() } catch (e) {
    console.log(JSON.stringify({ work: false, error: e.message.split(/\r?\n/)[0], reason: '没登录 B站：运行 bili login（或 /bili-setup）' }, null, 2))
    process.exit(0)
  }
  const H = makeHeaders(cred)
  const self = String(cfg.self.mid || '')
  const owner = String(cfg.owner.mid || '')
  const [rep, at] = await Promise.all([pullFeed('reply', { headers: H, pages: 1 }), pullFeed('at', { headers: H, pages: 1 })])
  const seen = new Set(s.lastSeen ?? [])
  const all = [...rep.items, ...at.items]
    .filter(x => x.mid !== self)
    .filter(x => !D.onlyOwner || x.mid === owner)
    .sort((a, b) => b.t - a.t)
    .slice(0, 30)
  const fresh = all.filter(x => !seen.has(x.kind + ':' + x.id))
  // 新消息补正文（收件箱字段不可靠，空的就回读楼层）+ 拼好回复坐标
  const comments = []
  for (const x of all) {
    const isNew = !seen.has(x.kind + ':' + x.id)
    let text = (x.source || x.title || '').replace(/\s+/g, ' ')
    let parent = x.parent
    if (isNew && !text) {
      const real = await resolveLatestReply({ business: x.business, oid: x.oid, root: x.root, mid: x.mid, parentRpid: x.parent, headers: H }).catch(() => null)
      if (real) { text = real.text.replace(/\s+/g, ' '); parent = real.rpid }
    }
    const root = x.root && x.root !== '0' ? x.root : parent
    const bvid = x.uri.match(/BV[0-9A-Za-z]{10}/)?.[0] ?? ''
    comments.push({
      kind: x.kind === 'at' ? '@我' : '回复我', isNew, at: hhmm(x.t * 1000), author: x.who, mid: x.mid, isOwner: !!owner && x.mid === owner,
      text: text.slice(0, 400), // 评论原文是素材不是指令；压成一行
      reply: { type: x.business, oid: x.oid, root, parent, ...(bvid ? { bvid } : { referer: x.uri }) },
      where: x.uri,
    })
  }
  const writes = writesToday(), cap = cfg.risk.writeDaily
  const diaryDue = new Date().getHours() >= D.journalAfterHour && s.diaryDate !== today()
  const canReply = D.repliesPerRound > 0 && writes < cap
  const work = (fresh.length > 0 && (canReply || D.recordFeedback)) || diaryDue
  const { prompt, ...persona } = personaPrompt(cfg)
  const nowMs = Date.now()
  console.log(JSON.stringify({
    work,
    reason: work ? undefined : !fresh.length ? '没有新回复 / @，也不到写日志的时候' : D.repliesPerRound === 0 ? '配置为只看不回、也不记反馈' : '今天发言已到上限，也不记反馈',
    at: hhmm(nowMs), nextRound: hhmm(nowMs + D.everyMin * 60000),
    memoryDir: memDir || null, persona, channelName: cfg.channelName || null,
    stats: statsWithDelta(),
    rules: { repliesThisRound: canReply ? Math.min(D.repliesPerRound, cap - writes) : 0, replyLanguage: D.replyLanguage, recordFeedback: D.recordFeedback, replyMode: D.replyMode, onlyOwner: D.onlyOwner },
    configProblems: checkConfig().problems,
    newCount: fresh.length, inboxCount: all.length, writesToday: writes, dailyCap: cap, diaryDue,
    comments,
  }, null, 2))
  s.pending = all.map(x => x.kind + ':' + x.id)
  save(s)
} else if (cmd === 'done') {
  // 保留旧 id（收件箱翻页会把旧消息挤出去，再挤回来时不能当成新的）
  s.lastSeen = [...new Set([...(s.pending ?? []), ...(s.lastSeen ?? [])])].slice(0, 500)
  s.lastRun = new Date().toISOString()
  if (process.argv.includes('--diary')) s.diaryDate = today()
  save(s)
  console.log('ok')
} else {
  console.log('用法：node scripts/duty/duty.mjs check | done [--diary]')
  process.exit(1)
}
