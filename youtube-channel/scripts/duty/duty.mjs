#!/usr/bin/env node
// 频道值守的巡视器：给 Claude Code 里常驻的值守会话用，配合 skill `channel-duty`
//
//   node scripts/duty/duty.mjs check          # 拉未回评论，和上一轮比 → 打印 JSON：这一轮要不要干活、干什么
//   node scripts/duty/duty.mjs done [--diary] # 这一轮做完了：记下看过的评论（--diary 记下今天已写值守日志）
//
// 它只读、只记状态，不回评论；回复走 `yt reply`（判重、限额、写 replies.md 都在那边）
// 状态文件：<共享记忆目录>/.duty-state.json；没设共享记忆就放 ~/.bili-ai/duty-state.json
import fs from 'node:fs'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { config } from '../yt/lib/config.mjs'
import { dshPath, homePath } from '../yt/lib/paths.mjs'
import { memoryDirOf } from '../yt/lib/memory.mjs'

const YT = fileURLToPath(new URL('../yt/commands/yt.mjs', import.meta.url))
const cfg = config()
const memDir = memoryDirOf(cfg)
const STATE = memDir ? path.join(memDir, '.duty-state.json') : homePath('.bili-ai', 'duty-state.json')
const DIARY_AFTER = Number(process.env.DUTY_DIARY_AFTER) || 21   // 这个钟点以后的第一轮写值守日志，一天一次

const today = () => new Date().toLocaleDateString('sv-SE')
const load = () => { try { return JSON.parse(fs.readFileSync(STATE, 'utf8')) } catch { return {} } }
const save = s => { fs.mkdirSync(path.dirname(STATE), { recursive: true }); fs.writeFileSync(STATE, JSON.stringify(s, null, 2)) }

function inbox() {
  const r = spawnSync(process.execPath, [YT, 'inbox', '--unreplied', '--n', '50', '--json'], { encoding: 'utf8', timeout: 120000 })
  if (r.status !== 0) throw new Error((r.stderr || r.stdout || 'yt inbox 失败').trim().slice(0, 500))
  return JSON.parse(r.stdout)
}

function repliesToday() {
  let n = 0
  try {
    for (const line of fs.readFileSync(dshPath('whale-log.jsonl'), 'utf8').split('\n')) {
      if (!line.includes('yt-reply-sent')) continue
      try { const j = JSON.parse(line); if (new Date(j.at).toLocaleDateString('sv-SE') === today()) n++ } catch {}
    }
  } catch {}
  return n
}

const cmd = process.argv[2]
const s = load()

if (cmd === 'check') {
  const list = inbox()
  const ids = list.map(t => t.id ?? t.threadId)
  const seen = new Set(s.lastSeen ?? [])
  const fresh = ids.filter(id => !seen.has(id))
  const replied = repliesToday(), cap = Number(cfg.youtube?.writeDaily) || 30
  const diaryDue = new Date().getHours() >= DIARY_AFTER && s.diaryDate !== today()
  const work = (fresh.length > 0 && replied < cap) || diaryDue
  console.log(JSON.stringify({
    work,
    reason: !work ? (fresh.length ? '今天回复已到上限' : '没有新评论，也不到写日志的时候') : undefined,
    memoryDir: memDir || null,
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
