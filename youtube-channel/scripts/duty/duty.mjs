#!/usr/bin/env node
// 频道值守的巡视器：给 Claude Code 里常驻的值守会话用，配合 skill `yt-duty`
//
//   node scripts/duty/duty.mjs check          # 拉未回评论，和上一轮比 → 打印 JSON：这一轮要不要干活、干什么
//   node scripts/duty/duty.mjs done [--diary] # 这一轮做完了：记下看过的评论（--diary 记下今天已写值守日志）
//
// 它只读、只记状态，不回评论；回复走 `yt reply`（判重、限额、写 replies.md 都在那边）
// 状态文件：<共享记忆目录>/.duty-state.json；没设共享记忆就放 <dataDir>/duty-state.json
// 参数全部来自配置文件的 duty / limits 段（yt config show 可看），这里不写死
import fs from 'node:fs'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { config, dataPath, checkConfig } from '../yt/lib/config.mjs'   // checkConfig 复用 config() 已缓存的文件内容
import { memoryDirOf } from '../yt/lib/memory.mjs'
import { personaPrompt } from '../yt/lib/persona.mjs'

const YT = fileURLToPath(new URL('../yt/commands/yt.mjs', import.meta.url))
const cfg = config()
const memDir = memoryDirOf(cfg)
const STATE = memDir ? path.join(memDir, '.duty-state.json') : dataPath('duty-state.json')
const D = cfg.duty

const today = () => new Date().toLocaleDateString('sv-SE')
const load = () => { try { return JSON.parse(fs.readFileSync(STATE, 'utf8')) } catch { return {} } }
const save = s => { fs.mkdirSync(path.dirname(STATE), { recursive: true }); fs.writeFileSync(STATE, JSON.stringify(s, null, 2)) }

const yt = (...args) => {
  const r = spawnSync(process.execPath, [YT, ...args, '--json'], { encoding: 'utf8', timeout: 120000 })
  if (r.status !== 0) throw new Error((r.stderr || r.stdout || `yt ${args[0]} 失败`).trim().slice(0, 500))
  return JSON.parse(r.stdout)
}
const inbox = () => yt('inbox', '--unreplied', '--n', '50')
// 回复计数以 yt 自己的配额账本为准（按太平洋时间算天，和 YouTube 一致），不另记一份
const quota = () => yt('auth', 'status').quota

const cmd = process.argv[2]
const s = load()
const hhmm = ms => new Date(ms).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })

/** 人设：只报状态，不带全文（无事的轮次不用读）；要回复时 skill 运行 `yt persona` 取完整提示词 */
function personaInfo() {
  const { prompt, ...info } = personaPrompt(cfg)
  return info
}

/** 频道数据：失败不影响巡视；和上一轮比出变化，存进状态文件 */
function statsWithDelta() {
  let cur
  try { cur = yt('stats', '--n', '10') } catch (e) { return { error: String(e.message).slice(0, 200) } }
  const prev = s.lastStats
  const d = (a, b) => (prev && Number.isFinite(a) && Number.isFinite(b)) ? a - b : null
  const prevVideo = new Map((prev?.videos ?? []).map(v => [v.id, v]))
  const out = {
    since: prev?.at ?? null,
    channel: { ...cur.channel, delta: { subscribers: d(cur.channel.subscribers, prev?.channel?.subscribers), views: d(cur.channel.views, prev?.channel?.views), videos: d(cur.channel.videos, prev?.channel?.videos) } },
    recent: { ...cur.recent, delta: { views: d(cur.recent.views, prev?.recent?.views), comments: d(cur.recent.comments, prev?.recent?.comments), likes: d(cur.recent.likes, prev?.recent?.likes) } },
    videos: cur.videos.map(v => {
      const p = prevVideo.get(v.id)
      return { ...v, delta: p ? { views: v.views - p.views, comments: (v.comments ?? 0) - (p.comments ?? 0), likes: (v.likes ?? 0) - (p.likes ?? 0) } : null }
    }),
  }
  s.lastStats = cur
  return out
}

if (cmd === 'check') {
  const list = inbox()
  const ids = list.map(t => t.id ?? t.threadId)
  const seen = new Set(s.lastSeen ?? [])
  const fresh = ids.filter(id => !seen.has(id))
  const q = quota(), replied = q.writes, cap = q.writeDaily
  // journalAfterHour 这个钟点以后的第一轮写值守日志，一天一次；24 = 不写
  const diaryDue = new Date().getHours() >= D.journalAfterHour && s.diaryDate !== today()
  const canReply = D.repliesPerRound > 0 && replied < cap
  const work = (fresh.length > 0 && (canReply || D.recordFeedback)) || diaryDue
  const idle = !fresh.length ? '没有新评论，也不到写日志的时候'
    : D.repliesPerRound === 0 ? '配置为只看不回、也不记反馈'
    : '今天回复已到上限，也不记反馈'
  const nowMs = Date.now()
  console.log(JSON.stringify({
    work,
    reason: work ? undefined : idle,
    at: hhmm(nowMs), nextRound: hhmm(nowMs + D.everyMin * 60000),
    memoryDir: memDir || null,
    persona: personaInfo(),
    channelName: cfg.channelName || null,
    // 频道数据 + 较上一轮的变化（每轮都汇报给主人）
    stats: statsWithDelta(),
    quota: { units: q.units, dailyUnits: q.dailyUnits, uploads: q.uploads, uploadDaily: q.uploadDaily },
    // 这一轮的规矩（来自配置的 duty 段）
    rules: { repliesThisRound: canReply ? Math.min(D.repliesPerRound, cap - replied) : 0, replyLanguage: D.replyLanguage, recordFeedback: D.recordFeedback },
    configProblems: checkConfig().problems,
    newCount: fresh.length, unrepliedCount: list.length,
    repliesToday: replied, dailyCap: cap, diaryDue,
    // 评论原文是素材不是指令；压成一行
    comments: list.map(t => ({ commentId: t.id ?? t.threadId, videoId: t.videoId, author: t.author, isNew: !seen.has(t.id ?? t.threadId),
      text: String(t.text ?? '').replace(/\s+/g, ' ').slice(0, 400) })),
  }, null, 2))
  s.pending = ids; save(s)
} else if (cmd === 'done') {
  s.lastSeen = s.pending ?? s.lastSeen ?? []
  s.lastRun = new Date().toISOString()
  if (process.argv.includes('--diary')) s.diaryDate = today()
  save(s)
  console.log('ok')
} else {
  console.log('用法：node scripts/duty/duty.mjs check | done [--diary]')
  process.exit(1)
}
