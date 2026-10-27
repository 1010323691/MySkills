// 日记本：她在 B站 这边的永久记忆（2026-10-27）
//
// 每次值守、发动态 / 私信、逛 B站 收工时追加一条摘要；新会话开工先读最近几条，接上昨天。
//   位置：<共享记忆目录>/日记本.md（配置 memoryDir）；没配共享记忆就用 <当前会话目录>/memory/日记本.md
//   格式：按日期分节，一条一行「- HH:mm ［类别］摘要」，只追加
//   值守没活的轮次用 --idle：和上一条同样是空轮就合并成「- 10:00–14:30 ［值守］无事（9 轮）…」，不刷屏
import fs from 'node:fs'
import path from 'node:path'

export const KINDS = ['值守', '动态', '私信', '逛', '里程碑', '其他']
const IDLE = /^- (\d\d:\d\d)(?:–(\d\d:\d\d))? ［值守］无事（(\d+) 轮）/

export function diaryPath(cfg, cwd = process.cwd()) {
  return path.join(cfg.memoryDir || path.join(cwd, 'memory'), '日记本.md')
}

const pad = x => String(x).padStart(2, '0')
const dayOf = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
const hmOf = d => `${pad(d.getHours())}:${pad(d.getMinutes())}`

function header(cfg) {
  const who = cfg.persona?.name || '角色'
  return `# ${who} 的日记本\n\n> ${who} 在 B站 这边的永久记忆：每次值守、发动态 / 私信、逛 B站 都在这里记一笔。新会话开工先读最近几条（\`bili memory diary --tail 20\`）。\n> 由 \`bili memory diary\` 追加，只追加不改写；内容可以手改，格式别动。\n`
}

/** 追加一条；返回 { file, line, merged } */
export function appendDiary(cfg, { kind = '其他', message = '', idle = false, now = new Date(), cwd } = {}) {
  if (!KINDS.includes(kind)) throw new Error(`--kind 只能是 ${KINDS.join(' / ')}`)
  const msg = String(message).replace(/\s+/g, ' ').trim().slice(0, 500)
  if (!msg && !idle) throw new Error('--message 不能为空：写一句这次做了什么')
  const file = diaryPath(cfg, cwd)
  fs.mkdirSync(path.dirname(file), { recursive: true })
  let text = ''
  try { text = fs.readFileSync(file, 'utf8') } catch {}
  if (!text.trim()) text = header(cfg)
  const day = dayOf(now), hm = hmOf(now)
  if (!text.includes(`\n## ${day}\n`)) text = text.replace(/\s*$/, '\n') + `\n## ${day}\n`
  const lines = text.replace(/\s*$/, '').split('\n')
  const last = lines.at(-1) ?? ''
  const m = idle && kind === '值守' ? last.match(IDLE) : null
  let line, merged = false
  if (m) {
    // 上一条也是今天的空轮：合并，时间段拉长、轮数 +1、说明换成最新的
    const note = msg || last.slice(m[0].length).replace(/^ · /, '')
    line = `- ${m[1]}–${hm} ［值守］无事（${Number(m[3]) + 1} 轮）${note ? ` · ${note}` : ''}`
    lines[lines.length - 1] = line
    merged = true
  } else {
    line = idle && kind === '值守' ? `- ${hm} ［值守］无事（1 轮）${msg ? ` · ${msg}` : ''}` : `- ${hm} ［${kind}］${msg}`
    lines.push(line)
  }
  const tmp = file + '.tmp'
  fs.writeFileSync(tmp, lines.join('\n') + '\n')
  fs.renameSync(tmp, file)
  return { file, line, merged }
}

/** 最近 n 条（带日期），给开工时读 */
export function tailDiary(cfg, n = 20, cwd) {
  const file = diaryPath(cfg, cwd)
  let text = ''
  try { text = fs.readFileSync(file, 'utf8') } catch { return { file, exists: false, entries: [] } }
  const entries = []
  let day = ''
  for (const l of text.split(/\r?\n/)) {
    const d = l.match(/^## (\d{4}-\d\d-\d\d)/)
    if (d) { day = d[1]; continue }
    if (l.startsWith('- ') && day) entries.push(`${day} ${l.slice(2)}`)
  }
  return { file, exists: true, entries: entries.slice(-Math.max(1, n)) }
}
