// 配置：一个 JSON 文件承载所有使用者自己的参数，代码里不写死
//
//   位置：$YOUTUBE_CHANNEL_CONFIG → ~/.youtube-channel/config.json（见 paths.mjs）
//   模板：插件根目录的 config.template.json；`yt config init` 复制过去，skill `channel-setup` 引导填写
//
// 没有配置文件也能跑（全用默认值），但 `yt config check` 会报出来
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { configPath, expandHome } from './paths.mjs'

export { configPath } from './paths.mjs'
export const templatePath = fileURLToPath(new URL('../../../config.template.json', import.meta.url))

/** 默认值：和模板一致，中性、不含任何个人信息 */
export const DEFAULTS = {
  channelName: '',
  dataDir: '~/.youtube-channel/data',
  memoryDir: '',
  personaFile: '',
  proxy: '',
  limits: { writeDaily: 30, writeGapSec: 120, uploadDaily: 10, dailyUnits: 8000, minGapMs: 1000 },
  duty: { everyMin: 30, repliesPerRound: 1, journalAfterHour: 21, replyLanguage: 'match', recordFeedback: true },
  publish: { privacy: 'public', category: '', playlist: '', tags: [], requireDossier: true },
}

const merge = (base, over) => {
  const out = { ...base }
  for (const [k, v] of Object.entries(over || {})) {
    out[k] = (v && typeof v === 'object' && !Array.isArray(v)) ? merge(base[k] ?? {}, v) : v
  }
  return out
}

/** 读原始配置文件：{ exists, user, error } */
export function readUserConfig() {
  let raw
  try { raw = fs.readFileSync(configPath, 'utf8') } catch { return { exists: false, user: {}, error: null } }
  try { return { exists: true, user: JSON.parse(raw.replace(/^﻿/, '')), error: null } }
  catch (e) { return { exists: true, user: {}, error: `配置文件不是合法 JSON：${e.message}` } }
}

let cache = null
/** 合并后的配置（带缓存）。另附 `youtube` 视图，给 yt 命令和共享记忆模块用 */
export function config() {
  if (cache) return cache
  const { user } = readUserConfig()
  const c = merge(DEFAULTS, user)
  c.dataDir = path.resolve(expandHome(c.dataDir || DEFAULTS.dataDir))
  c.memoryDir = c.memoryDir ? expandHome(c.memoryDir) : ''
  c.personaFile = c.personaFile ? expandHome(c.personaFile) : ''
  c.youtube = { ...c.limits, proxy: c.proxy, memoryDir: c.memoryDir }
  cache = c
  return c
}

/** 数据目录下的路径：令牌、账本、活动日志 */
export const dataPath = (...parts) => path.join(config().dataDir, ...parts)

const int = (v, lo, hi) => Number.isInteger(v) && v >= lo && v <= hi
/** 检查配置：返回问题清单（空 = 没问题） */
export function checkConfig() {
  const { exists, error } = readUserConfig()
  const c = config()
  const problems = []
  if (!exists) problems.push(`还没有配置文件：${configPath}（运行 yt config init）`)
  if (error) problems.push(error)
  if (!c.memoryDir) problems.push('memoryDir 没填：值守和工作室之间没有共享记忆')
  else if (!path.isAbsolute(c.memoryDir)) problems.push('memoryDir 必须是绝对路径（可以用 ~ 开头）')
  if (c.personaFile && !fs.existsSync(c.personaFile)) problems.push(`personaFile 指向的文件不存在：${c.personaFile}`)
  if (c.proxy && !/^(https?|socks5?):\/\/.+/.test(c.proxy)) problems.push('proxy 要写成 http://主机:端口 这样的地址')
  const L = c.limits, D = c.duty, P = c.publish
  if (!int(L.writeDaily, 1, 100)) problems.push('limits.writeDaily 要是 1–100 的整数')
  if (!int(L.writeGapSec, 30, 86400)) problems.push('limits.writeGapSec 至少 30')
  if (!int(L.uploadDaily, 0, 100)) problems.push('limits.uploadDaily 要是 0–100 的整数')
  if (!int(L.dailyUnits, 100, 10000)) problems.push('limits.dailyUnits 要在 100–10000 之间（官方默认每天 10000）')
  if (!int(D.everyMin, 10, 720)) problems.push('duty.everyMin 要是 10–720 的整数（分钟）')
  if (!int(D.repliesPerRound, 0, 10)) problems.push('duty.repliesPerRound 要是 0–10 的整数')
  if (!int(D.journalAfterHour, 0, 24)) problems.push('duty.journalAfterHour 要是 0–24 的整数（24 = 不写值守日志）')
  if (!['match', 'en', 'ja', 'zh'].includes(D.replyLanguage)) problems.push('duty.replyLanguage 只能是 match / en / ja / zh')
  if (!['public', 'unlisted', 'private'].includes(P.privacy)) problems.push('publish.privacy 只能是 public / unlisted / private')
  if (P.playlist && !/^[A-Za-z0-9_-]+$/.test(P.playlist)) problems.push('publish.playlist 要是播放列表 ID（形如 PLxxxx）')
  if (!Array.isArray(P.tags)) problems.push('publish.tags 要是字符串数组')
  return { path: configPath, exists, problems }
}

/** 从模板生成配置文件；已有就不动 */
export function initConfig() {
  if (fs.existsSync(configPath)) return { path: configPath, created: false }
  fs.mkdirSync(path.dirname(configPath), { recursive: true })
  fs.copyFileSync(templatePath, configPath)
  cache = null
  return { path: configPath, created: true }
}
