// 配置：一个 JSON 文件承载所有使用者自己的参数，代码里不写死
//
//   位置：$BILIBILI_CHANNEL_CONFIG → ~/.bilibili-channel/config.json（见 paths.mjs）
//   模板：插件根目录的 config.template.json；`bili config init` 复制过去，skill `bili-setup` 引导填写
//
// 字段沿用旧版 dsh-bili-whale 的形状（self / owner / persona / preferences / risk / quota / share / notify），
// 原有命令照读不改；新增 dataDir / memoryDir / persona.file / persona.notes / duty
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { configPath, expandHome, DATA_DIR } from './paths.mjs'

export { configPath } from './paths.mjs'
export const templatePath = fileURLToPath(new URL('../../../config.template.json', import.meta.url))

/** 默认值：中性、不含任何个人信息 */
export const DEFAULTS = {
  channelName: '',
  dataDir: '~/.bilibili-channel/data',
  memoryDir: '',
  // 自己的号（她用的 B站 账号）：登录后 `bili login status` 能看到 mid
  self: { mid: '', name: '' },
  // 主人（分享型评论要 @ 的人、私信只发给他）：mid 用于白名单，name 用于正文里的 @昵称
  owner: { mid: '', name: '' },
  aliases: [],
  persona: { name: '', ownerTitle: '', selfClaim: '', file: '', notes: [], diaryTitle: '今日摘要' },
  // 刷 B站 时的口味：选题器按 like 捞候选，dislike 的跳过
  preferences: { like: [], dislike: [], keywords: [] },
  risk: { minGapMs: 1500, readHourly: 600, readDaily: 3000, writeHourly: 12, writeDaily: 30, writeGapSec: 120, dmGapSec: 60 },
  quota: { shareDaily: 3 },
  share: { aiCommentGuard: false, aiThreshold: 30, enabled: true, via: 'comment', minScore: 13, silentAfterDays: 3 },
  notify: { type: 'none', url: '', template: 'text', cmd: '' },
  // 值守：每轮间隔、每轮最多回几条、几点后写值守日志、回复语言、要不要记反馈、要不要先审后发、汇报里要不要逐个投稿的数据
  duty: { everyMin: 30, repliesPerRound: 1, journalAfterHour: 21, replyLanguage: 'match', recordFeedback: true, replyMode: 'direct', onlyOwner: false, maxAgeHours: 72, videoStats: true },
  // 旧版字段：几个命令还会读，保持中性默认
  listen: { comment: false, commentIntervalSec: 60, scope: 'both', oncePerPerson: true, allDay: false, dm: true, dmIntervalSec: 60, live: false, liveRoom: '', liveScope: 'owner' },
  diary: { push: false },
}

const merge = (base, over) => {
  const out = { ...base }
  for (const [k, v] of Object.entries(over || {})) {
    out[k] = (v && typeof v === 'object' && !Array.isArray(v)) ? merge(base[k] ?? {}, v) : v
  }
  return out
}

let raw = null
/** 读原始配置文件（带缓存）：{ exists, user, error } */
export function readUserConfig() {
  if (raw) return raw
  let text
  try { text = fs.readFileSync(configPath, 'utf8') } catch { return (raw = { exists: false, user: {}, error: null }) }
  let user
  try { user = JSON.parse(text.replace(/^﻿/, '')) }
  catch (e) { return (raw = { exists: true, user: {}, error: `配置文件不是合法 JSON：${e.message}` }) }
  if (!user || typeof user !== 'object' || Array.isArray(user)) return (raw = { exists: true, user: {}, error: '配置文件最外层要是一个 { … } 对象' })
  return (raw = { exists: true, user, error: null })
}

let cache = null
/** 合并后的配置（带缓存） */
export function config() {
  if (cache) return cache
  const { user } = readUserConfig()
  const c = merge(DEFAULTS, user)
  c.dataDir = DATA_DIR
  c.memoryDir = c.memoryDir ? expandHome(c.memoryDir) : ''
  c.persona.file = c.persona.file ? expandHome(c.persona.file) : ''
  // 共享记忆模块按 youtube.memoryDir 找目录（和 youtube-channel 包同一份代码）
  c.youtube = { memoryDir: c.memoryDir }
  c.__hasUserFile = Object.keys(user).length > 0
  cache = c
  return c
}

const int = (v, lo, hi) => Number.isInteger(v) && v >= lo && v <= hi
const MID = v => v === '' || /^\d{1,20}$/.test(String(v))
/** 检查配置：返回问题清单（空 = 没问题） */
export function checkConfig() {
  const { exists, error } = readUserConfig()
  const c = config()
  const problems = []
  if (!exists) problems.push(`还没有配置文件：${configPath}（运行 bili config init）`)
  if (error) problems.push(error)
  if (!c.memoryDir) problems.push('memoryDir 没填：值守和工作室之间没有共享记忆')
  else if (!path.isAbsolute(c.memoryDir)) problems.push('memoryDir 必须是绝对路径（可以用 ~ 开头）')
  if (!MID(c.self.mid)) problems.push('self.mid 要是纯数字（B站 UID）')
  if (!MID(c.owner.mid)) problems.push('owner.mid 要是纯数字（B站 UID）')
  if (!c.owner.mid) problems.push('owner.mid 没填：私信报备、只认主人回复、@主人 都用不了')
  // 主人和她共用一个号是合法用法（不算问题，不会每轮值守都报 ⚠），只在 config check 里提示一次
  const notes = []
  if (c.owner.mid && String(c.owner.mid) === String(c.self.mid)) notes.push('owner.mid 和 self.mid 是同一个号：私信报备（不能给自己发）、分享时 @主人、duty.onlyOwner 用不了，其余功能照常；要用这些就让她换一个单独的号')
  const P = c.persona
  if (P.file && !fs.existsSync(P.file)) problems.push(`persona.file 指向的文件不存在：${P.file}`)
  if (!P.name && !P.file) problems.push('persona 没填（至少填 name 或 file）：回复没有人设可依')
  if (!Array.isArray(P.notes)) problems.push('persona.notes 要是字符串数组')
  for (const k of ['like', 'dislike', 'keywords']) if (!Array.isArray(c.preferences[k])) problems.push(`preferences.${k} 要是字符串数组`)
  const D = c.duty, R = c.risk
  if (!int(D.everyMin, 10, 720)) problems.push('duty.everyMin 要是 10–720 的整数（分钟）')
  if (!int(D.repliesPerRound, 0, 10)) problems.push('duty.repliesPerRound 要是 0–10 的整数')
  if (!int(D.journalAfterHour, 0, 24)) problems.push('duty.journalAfterHour 要是 0–24 的整数（24 = 不写值守日志）')
  if (!['match', 'en', 'ja', 'zh'].includes(D.replyLanguage)) problems.push('duty.replyLanguage 只能是 match / en / ja / zh')
  if (!int(D.maxAgeHours, 1, 720)) problems.push('duty.maxAgeHours 要是 1–720 的整数（小时）')
  if (typeof D.videoStats !== 'boolean') problems.push('duty.videoStats 只能是 true / false')
  if (!['direct', 'review'].includes(D.replyMode)) problems.push('duty.replyMode 只能是 direct（直接回）或 review（先进待审队列）')
  if (!int(R.writeDaily, 1, 200)) problems.push('risk.writeDaily 要是 1–200 的整数')
  if (!int(R.writeGapSec, 30, 86400)) problems.push('risk.writeGapSec 至少 30（B站 风控）')
  if (!['none', 'desktop', 'webhook', 'command'].includes(c.notify.type)) problems.push('notify.type 只能是 none / desktop / webhook / command')
  return { path: configPath, exists, problems, notes }
}

/** 从模板生成配置文件；已有就不动 */
export function initConfig() {
  if (fs.existsSync(configPath)) return { path: configPath, created: false }
  fs.mkdirSync(path.dirname(configPath), { recursive: true })
  fs.copyFileSync(templatePath, configPath)
  cache = raw = null
  return { path: configPath, created: true }
}
