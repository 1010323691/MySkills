// YouTube 平台层（2026-10-26 加，阶段 1）：OAuth 登录 + 看自己频道视频的评论区 + 回复评论
//
// 和 B 站那套的关系：只换「平台层」，克制的规矩照搬 ——
//   · 写操作必须显式 --dry / --go，单条、不批量
//   · 只回【自己频道视频下】的评论（代码校验 snippet.channelId，不靠自觉 ✓）
//   · 同一条评论只回一次；结果不确定（网络断在半路）就禁止自动重发，人工核查后 forget 才放行
//   · 本地配额预算 + 写冷却 + 撞 quotaExceeded / 429 全局暂停
//
// 凭据：OAuth 客户端与令牌都在配置的 dataDir 下（默认 ~/.youtube-channel/data/），换机器拷这个目录就带走 ✓
//   文件权限 600，令牌永远不打印 ✓
//
// 官方配额（默认每天 10,000 单位，太平洋时间零点重置）：列表类 1 单位，comments.insert 50 单位。
//
// OAuth（PKCE、换令牌、刷新、撤销）用 Google 官方的 google-auth-library，不自己实现协议细节 ✓
// YouTube 接口本身仍用 fetch：每个请求都要先过本地配额闸，自己控制更直接
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import http from 'node:http'
import { setTimeout as delay } from 'node:timers/promises'
import { OAuth2Client, CodeChallengeMethod } from 'google-auth-library'

export const YT_SCOPE = 'https://www.googleapis.com/auth/youtube.force-ssl'
const API = 'https://www.googleapis.com/youtube/v3/'
export const YT_DEFAULTS = { minGapMs: 1000, dailyUnits: 8000, writeDaily: 30, writeGapSec: 120, uploadDaily: 10 }
export const MAX_REPLY_CHARS = 10000
const UPLOAD = 'https://www.googleapis.com/upload/youtube/v3/'
const UPLOAD_CHUNK = 8 * 1024 * 1024   // 断点续传的分块必须是 256 KB 的整数倍
const VIDEO_TYPES = { '.mp4': 'video/mp4', '.m4v': 'video/x-m4v', '.mov': 'video/quicktime', '.mkv': 'video/x-matroska', '.webm': 'video/webm',
  '.avi': 'video/x-msvideo', '.wmv': 'video/x-ms-wmv', '.flv': 'video/x-flv', '.mpg': 'video/mpeg', '.mpeg': 'video/mpeg', '.3gp': 'video/3gpp', '.ts': 'video/mp2t' }
const IMAGE_TYPES = { '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png' }
const WRITE_COST = 50
const ID = /^[A-Za-z0-9_-]+$/

export class YouTubeError extends Error {
  constructor(message, code = 'YT_ERROR') { super(message); this.name = 'YouTubeError'; this.code = code }
}

export const pacificDay = ms => new Date(ms).toLocaleDateString('sv-SE', { timeZone: 'America/Los_Angeles' })
/** 下一个太平洋时间零点（配额重置点）；先按小时再按分钟逼近，夏令时也对 ✓ */
export function nextPacificMidnight(ms) {
  const day = pacificDay(ms)
  let t = ms
  while (pacificDay(t) === day) t += 3600000
  t -= 3600000
  while (pacificDay(t) === day) t += 60000
  return t
}

/** 读配置里的 youtube 段，并夹到安全范围（0 / 负数 / 超过官方配额都不接受） */
export function youtubeSettings(cfg = {}) {
  const out = { ...YT_DEFAULTS }
  for (const key of Object.keys(out)) {
    const n = Number(cfg[key])
    // uploadDaily 允许 0 = 禁止上传；其余 0 当没填（防手滑关掉闸门）
    if (Number.isFinite(n) && (n > 0 || (key === 'uploadDaily' && n === 0))) out[key] = Math.floor(n)
  }
  out.minGapMs = Math.max(500, out.minGapMs)
  out.dailyUnits = Math.min(10000, out.dailyUnits)
  out.writeDaily = Math.min(100, out.writeDaily)
  out.uploadDaily = Math.min(100, out.uploadDaily)   // 官方上传额度每天 100 次
  out.writeGapSec = Math.max(30, out.writeGapSec)
  return out
}

/** google-auth-library 抛的是 GaxiosError：response 为空 = 网络不通；invalid_grant = 授权失效 */
function authError(e, what) {
  if (e instanceof YouTubeError) return e
  const data = e?.response?.data ?? {}
  if (data.error === 'invalid_grant') return new YouTubeError('授权已失效（被撤销，或应用处于「测试」状态时 7 天过期）：请重新运行 yt auth login', 'YT_AUTH')
  if (!e?.response) return new YouTubeError(`连不上 Google 授权服务器：${e?.code ?? e?.message}（国内网络可能要在配置里填 youtube.proxy）`, 'YT_NET')
  return new YouTubeError(`${what}失败：HTTP ${e.response.status}${data.error ? ' / ' + data.error : ''}${data.error_description ? '：' + data.error_description : ''}`, 'YT_AUTH')
}

function readJson(file, fallback) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8').replace(/^﻿/, '')) }
  catch (e) { if (e.code === 'ENOENT') return fallback; throw new YouTubeError(`文件损坏，请检查或删除后重来：${file}`, 'YT_STATE') }
}
function writeJson(file, value, secret = false) {
  fs.mkdirSync(path.dirname(file), { recursive: true })
  const temp = file + '.' + process.pid + '.' + crypto.randomUUID() + '.tmp'
  try {
    fs.writeFileSync(temp, JSON.stringify(value, null, 2) + '\n', secret ? { mode: 0o600 } : undefined)
    fs.renameSync(temp, file)
    if (secret) { try { fs.chmodSync(file, 0o600) } catch {} }
  } finally { fs.rmSync(temp, { force: true }) }
}

// 跨进程锁：只包住「读-改-写」本地状态，从不包住网络请求
async function locked(lockFile, fn) {
  fs.mkdirSync(path.dirname(lockFile), { recursive: true })
  const deadline = Date.now() + 10000
  let fd
  while (fd === undefined) {
    try { fd = fs.openSync(lockFile, 'wx'); fs.writeFileSync(fd, JSON.stringify({ pid: process.pid })) }
    catch (e) {
      if (e.code !== 'EEXIST') throw e
      try {
        let pid
        try { pid = JSON.parse(fs.readFileSync(lockFile, 'utf8')).pid } catch {}
        let dead = false
        if (Number.isInteger(pid) && pid > 0) { try { process.kill(pid, 0) } catch (x) { dead = x.code === 'ESRCH' } }
        if (dead || (!pid && Date.now() - fs.statSync(lockFile).mtimeMs > 10000)) { fs.unlinkSync(lockFile); continue }
      } catch {}
      if (Date.now() >= deadline) throw new YouTubeError('YouTube 状态锁繁忙，本次停止；请稍后再试', 'YT_LOCK')
      await delay(25)
    }
  }
  try { return await fn() } finally { fs.closeSync(fd); fs.rmSync(lockFile, { force: true }) }
}

/** Google Cloud 下载的客户端 JSON 有 {installed:{…}} / {web:{…}} / 扁平 三种形态 */
export function parseClientJson(raw) {
  let j
  try { j = typeof raw === 'string' ? JSON.parse(raw.replace(/^﻿/, '')) : raw } catch { throw new YouTubeError('OAuth 客户端文件不是合法 JSON', 'YT_CLIENT') }
  const c = j?.installed ?? j?.web ?? j ?? {}
  const client_id = String(c.client_id ?? '').trim(), client_secret = String(c.client_secret ?? '').trim()
  if (!client_id.endsWith('.apps.googleusercontent.com') || !client_secret) {
    throw new YouTubeError('OAuth 客户端缺少 client_id / client_secret（要「桌面应用」类型的那个 JSON）', 'YT_CLIENT')
  }
  return { client_id, client_secret }
}

function plain(comment) {
  const s = comment?.snippet ?? {}
  return {
    id: comment?.id,
    author: s.authorDisplayName ?? '',
    authorChannelId: s.authorChannelId?.value ?? '',
    text: s.textDisplay ?? s.textOriginal ?? '',
    likes: Number(s.likeCount ?? 0),
    publishedAt: s.publishedAt ?? null,
  }
}

export function createYouTube({ directory, fetch: transport = fetch, now = Date.now, sleep = delay, settings = () => YT_DEFAULTS, uploadChunk = UPLOAD_CHUNK } = {}) {
  if (!directory) throw new Error('createYouTube 需要 directory')
  const file = name => path.join(directory, name)
  const CLIENT = file('youtube-client.json'), TOKEN = file('youtube-token.json')
  const STATE = file('youtube-state.json'), REPLIED = file('youtube-replied.json')

  function loadClient() {
    const raw = readJson(CLIENT, null)
    if (!raw) throw new YouTubeError(`还没有 OAuth 客户端：在 Google Cloud 建「桌面应用」类型的 OAuth 客户端，下载 JSON 后运行 yt auth client <文件>`, 'YT_CLIENT')
    return parseClientJson(raw)
  }
  function saveClient(raw) {
    const client = parseClientJson(raw)
    writeJson(CLIENT, client, true)
    return { client_id: client.client_id }
  }

  const oauth = (client, redirectUri) => new OAuth2Client({ clientId: client.client_id, clientSecret: client.client_secret, redirectUri,
    transporterOptions: { fetchImplementation: transport, timeout: 30000 } })

  async function accessToken({ force = false } = {}) {
    const t = readJson(TOKEN, null)
    if (!t?.refresh_token) throw new YouTubeError('还没登录 YouTube：运行 yt auth login', 'YT_AUTH')
    if (!force && t.access_token && Number(t.expires_at) - 60000 > now()) return t.access_token
    return locked(TOKEN + '.lock', async () => {
      const cur = readJson(TOKEN, null)
      if (!cur?.refresh_token) throw new YouTubeError('还没登录 YouTube：运行 yt auth login', 'YT_AUTH')
      // 另一个进程刚刷新过就直接用（force 时例外：那说明这个令牌刚被服务器拒绝）
      if (!force && cur.access_token && Number(cur.expires_at) - 60000 > now()) return cur.access_token
      const o = oauth(loadClient())
      o.setCredentials({ refresh_token: cur.refresh_token })
      let token
      try { token = (await o.getAccessToken()).token } catch (e) { throw authError(e, '刷新令牌') }
      if (!token) throw new YouTubeError('刷新令牌失败：Google 没有返回 access_token', 'YT_AUTH')
      const expires = Number(o.credentials.expiry_date)
      writeJson(TOKEN, { ...cur, access_token: token, expires_at: Number.isFinite(expires) ? expires : now() + 3600000 }, true)
      return token
    })
  }

  // 配额与节流：先在锁里预订（单位数、写冷却、最小间隔），再出锁发请求
  //   kind：read 读 / reply 回复（算冷却与每日回复条数）/ write 其它写（封面、播放列表，只算单位）
  //         / upload 上传（官方独立的上传额度，不占 10,000 单位；本地另算每日上传个数）
  async function reserve(units, kind = 'read') {
    const cfg = settings()
    const slot = await locked(STATE + '.lock', () => {
      const s = readJson(STATE, {})
      const t = now()
      if (Number(s.until ?? 0) > t) throw new YouTubeError(`YouTube 请求已暂停，${new Date(s.until).toISOString()} 后再试（${s.reason ?? '平台限制'}）`, 'YT_PAUSED')
      const day = pacificDay(t)
      if (s.day !== day) Object.assign(s, { day, units: 0, writes: 0, uploads: 0 })
      if (kind === 'upload') {
        if (Number(s.uploadsUntil ?? 0) > t) throw new YouTubeError(`YouTube 上传额度已用尽，${new Date(s.uploadsUntil).toISOString()} 后再试`, 'YT_PAUSED')
        if (cfg.uploadDaily === 0) throw new YouTubeError('配置里 limits.uploadDaily 是 0：禁止上传', 'YT_BUDGET')
        if (Number(s.uploads ?? 0) >= cfg.uploadDaily) throw new YouTubeError(`今天的上传额度已用完（${cfg.uploadDaily} 个，太平洋时间零点重置）`, 'YT_BUDGET')
      } else if (Number(s.units ?? 0) + units > cfg.dailyUnits) throw new YouTubeError(`已达到本地 YouTube 配额预算（${s.units}/${cfg.dailyUnits} 单位，太平洋时间零点重置）`, 'YT_BUDGET')
      if (kind === 'reply') {
        const gap = cfg.writeGapSec * 1000
        if (s.lastWrite && t - s.lastWrite < gap) throw new YouTubeError(`写操作冷却中，还要等 ${Math.ceil((s.lastWrite + gap - t) / 1000)} 秒`, 'YT_COOLDOWN')
        if (Number(s.writes ?? 0) >= cfg.writeDaily) throw new YouTubeError(`今天的回复额度已用完（${cfg.writeDaily} 条）`, 'YT_BUDGET')
      }
      const at = Math.max(t, Number(s.nextAt ?? 0))
      if (at - t > 30000) throw new YouTubeError('请求队列已满，本次停止', 'YT_BUDGET')
      s.nextAt = at + cfg.minGapMs
      if (kind === 'upload') s.uploads = Number(s.uploads ?? 0) + 1
      else s.units = Number(s.units ?? 0) + units
      if (kind === 'reply') { s.writes = Number(s.writes ?? 0) + 1; s.lastWrite = t }
      writeJson(STATE, s)
      return at
    })
    await sleep(Math.max(0, slot - now()))
  }
  function pause(until, reason) {
    return locked(STATE + '.lock', () => {
      const s = readJson(STATE, {})
      s.until = Math.max(Number(s.until ?? 0), until)
      s.reason = reason
      writeJson(STATE, s)
    })
  }

  async function api(resource, params, { method = 'GET', body, token, kind = method === 'GET' ? 'read' : 'reply', units } = {}) {
    const writing = method !== 'GET'
    await reserve(units ?? (writing ? WRITE_COST : 1), kind)
    const url = API + resource + '?' + new URLSearchParams(params)
    const send = async tok => {
      try {
        return await transport(url, { method, signal: AbortSignal.timeout(30000), body: body ? JSON.stringify(body) : undefined,
          headers: { authorization: 'Bearer ' + tok, accept: 'application/json', ...(body ? { 'content-type': 'application/json' } : {}) } })
      } catch (e) {
        if (writing) throw new YouTubeError('发送结果不确定（网络断在半路），已禁止自动重发；请先用 yt thread 回读核查', 'YT_UNCERTAIN')
        throw new YouTubeError('YouTube 网络请求失败：' + (e.cause?.code ?? e.message) + '（国内网络可能要在配置里填 youtube.proxy）', 'YT_NET')
      }
    }
    let res = await send(token ?? await accessToken())
    // 401 只有在「请求根本没被受理」时出现，重试同一请求不会重复发送 ✓
    if (res.status === 401 && !token) res = await send(await accessToken({ force: true }))
    let j = null
    try { j = await res.json() } catch {}
    if (res.ok) return j ?? {}
    throw await failure(res, j, resource)
  }

  /** 把失败的响应翻译成人话；撞配额 / 限流顺手全局暂停（上传额度单独暂停） */
  async function failure(res, j, what) {
    const reason = j?.error?.errors?.[0]?.reason ?? ''
    const detail = j?.error?.message ?? ''
    if (['quotaExceeded', 'dailyLimitExceeded'].includes(reason)) {
      await pause(nextPacificMidnight(now()), 'YouTube 配额用尽（' + reason + '）')
    } else if (reason === 'uploadLimitExceeded') {
      await locked(STATE + '.lock', () => { const s = readJson(STATE, {}); s.uploadsUntil = nextPacificMidnight(now()); writeJson(STATE, s) })
    } else if (res.status === 429 || ['rateLimitExceeded', 'userRateLimitExceeded'].includes(reason)) {
      const retry = Number(res.headers?.get?.('retry-after'))
      await pause(now() + Math.max(600000, Number.isFinite(retry) ? retry * 1000 : 0), 'YouTube 限流（' + (reason || 'HTTP 429') + '）')
    }
    const hint = { commentsDisabled: '该视频关闭了评论', insufficientPermissions: '授权范围不足，请重新 yt auth login', forbidden: '没有权限做这个操作',
      commentNotFound: '找不到这条评论（可能已被删除）', videoNotFound: '找不到这个视频', processingFailure: 'YouTube 处理失败，稍后核查是否已发出',
      uploadLimitExceeded: '这个频道今天的上传次数已到 YouTube 上限', invalidTitle: '标题不合法（1–100 字，不能有 < >）', invalidDescription: '简介不合法（≤5000 字节，不能有 < >）',
      invalidTags: '标签不合法（合计 ≤500 字）', invalidPublishAt: '定时发布时间不合法（要是将来的时间，且视频为私享）',
      mediaBodyTooLarge: '封面文件太大（YouTube 要求 ≤2MB）', playlistNotFound: '找不到这个播放列表（要是你自己频道的）' }[reason]
    return new YouTubeError(`YouTube ${what} 返回 HTTP ${res.status}${reason ? ' / ' + reason : ''}：${hint ?? detail}`, res.status === 401 ? 'YT_AUTH' : 'YT_HTTP')
  }

  async function fetchMe(token) {
    const j = await api('channels', { part: 'snippet,contentDetails', mine: 'true' }, { token })
    const c = j.items?.[0]
    if (!c) return null
    return { id: c.id, title: c.snippet?.title ?? '', handle: c.snippet?.customUrl ?? '', uploads: c.contentDetails?.relatedPlaylists?.uploads ?? '' }
  }
  /** 当前登录的频道；登录时已缓存，一般不花配额 */
  async function me({ fresh = false } = {}) {
    const t = readJson(TOKEN, null)
    if (!t?.refresh_token) throw new YouTubeError('还没登录 YouTube：运行 yt auth login', 'YT_AUTH')
    if (t.channel?.id && !fresh) return t.channel
    const channel = await fetchMe()
    if (!channel) throw new YouTubeError('这个 Google 账号下没有 YouTube 频道', 'YT_AUTH')
    await locked(TOKEN + '.lock', () => { const cur = readJson(TOKEN, {}); writeJson(TOKEN, { ...cur, channel }, true) })
    return channel
  }

  /**
   * 本机回环授权（Google 给桌面应用的标准做法）+ PKCE：
   *   起一个只监听 127.0.0.1 的临时端口 → 浏览器同意后 Google 带着 code 跳回来 → 换令牌
   * 新令牌验证通过（真能读到频道）才覆盖旧的 ✓ 半路失败不动原来的登录态
   */
  async function login({ open = () => {}, timeoutMs = 300000 } = {}) {
    const client = loadClient()
    const state = crypto.randomBytes(16).toString('base64url')
    const server = http.createServer()
    await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve) })
    const redirect = `http://127.0.0.1:${server.address().port}`
    const o = oauth(client, redirect)
    const { codeVerifier, codeChallenge } = await o.generateCodeVerifierAsync()
    const url = o.generateAuthUrl({ access_type: 'offline', prompt: 'consent', scope: [YT_SCOPE],
      code_challenge_method: CodeChallengeMethod.S256, code_challenge: codeChallenge, state })
    let timer
    const code = await new Promise((resolve, reject) => {
      timer = setTimeout(() => reject(new YouTubeError(`授权超时（${Math.round(timeoutMs / 60000)} 分钟），请重新运行 yt auth login`, 'YT_AUTH')), timeoutMs)
      server.on('request', (req, res) => {
        const u = new URL(req.url, redirect)
        if (u.pathname !== '/') { res.writeHead(404).end(); return }
        const got = u.searchParams.get('code')
        const ok = !!got && u.searchParams.get('state') === state
        res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' })
        res.end(ok ? '<p>授权完成，可以关掉这个页面回到 DSH。</p>' : '<p>授权没有完成，请回到 DSH 重新运行 yt auth login。</p>')
        if (ok) resolve(got)
        else reject(new YouTubeError('授权被拒绝或状态校验失败：' + (u.searchParams.get('error') ?? 'state mismatch'), 'YT_AUTH'))
      })
      Promise.resolve().then(() => open(url)).catch(() => {})
    }).finally(() => { clearTimeout(timer); server.close(); server.closeAllConnections?.() })
    let j
    try { j = (await o.getToken({ code, codeVerifier })).tokens } catch (e) { throw authError(e, '换取令牌') }
    if (!String(j.scope ?? '').split(' ').includes(YT_SCOPE)) throw new YouTubeError('授权时没有勾选「管理你的 YouTube 账号」权限，请重新授权并勾选', 'YT_AUTH')
    if (!j.refresh_token) throw new YouTubeError('Google 没有返回 refresh_token：到 https://myaccount.google.com/permissions 移除本应用的授权后重试', 'YT_AUTH')
    const channel = await fetchMe(j.access_token)
    if (!channel) throw new YouTubeError('这个 Google 账号下没有 YouTube 频道（先在 YouTube 建一个频道）', 'YT_AUTH')
    const expires = Number(j.expiry_date)
    await locked(TOKEN + '.lock', () => writeJson(TOKEN, { access_token: j.access_token, refresh_token: j.refresh_token,
      expires_at: Number.isFinite(expires) ? expires : now() + 3600000, scope: j.scope, channel, at: new Date(now()).toISOString() }, true))
    return channel
  }

  async function logout() {
    const t = readJson(TOKEN, null)
    if (!t) return { removed: false }
    // 尽量在 Google 侧也撤销；撤销失败不影响本地删除
    let revoked = false
    try { await oauth(loadClient()).revokeToken(t.refresh_token ?? t.access_token ?? ''); revoked = true } catch {}
    fs.rmSync(TOKEN, { force: true })
    return { removed: true, revoked }
  }

  function status() {
    const t = readJson(TOKEN, null)
    const cfg = settings()
    const s = readJson(STATE, {})
    const today = pacificDay(now()) === s.day
    let client = false
    try { loadClient(); client = true } catch {}
    return { client, loggedIn: !!t?.refresh_token, channel: t?.channel ?? null,
      quota: { day: pacificDay(now()), units: today ? Number(s.units ?? 0) : 0, dailyUnits: cfg.dailyUnits, writes: today ? Number(s.writes ?? 0) : 0, writeDaily: cfg.writeDaily,
        uploads: today ? Number(s.uploads ?? 0) : 0, uploadDaily: cfg.uploadDaily },
      pausedUntil: Number(s.until ?? 0) > now() ? new Date(s.until).toISOString() : null, pauseReason: Number(s.until ?? 0) > now() ? s.reason : null }
  }

  /** 自己频道最近上传的视频（含评论数） */
  async function myVideos({ n = 10 } = {}) {
    const ch = await me()
    if (!ch.uploads) return []
    const list = await api('playlistItems', { part: 'snippet,contentDetails', playlistId: ch.uploads, maxResults: String(Math.min(50, Math.max(1, n))) })
    const ids = (list.items ?? []).map(it => it.contentDetails?.videoId).filter(Boolean)
    if (!ids.length) return []
    const stats = await api('videos', { part: 'snippet,statistics', id: ids.join(',') })
    const byId = new Map((stats.items ?? []).map(v => [v.id, v]))
    return ids.map(id => {
      const v = byId.get(id)
      return { id, title: v?.snippet?.title ?? '', publishedAt: v?.snippet?.publishedAt ?? null,
        views: Number(v?.statistics?.viewCount ?? 0), comments: v?.statistics?.commentCount === undefined ? null : Number(v.statistics.commentCount) }
    })
  }

  function thread(item, myId) {
    const s = item?.snippet ?? {}
    const top = plain(s.topLevelComment)
    const replies = (item?.replies?.comments ?? []).map(plain).map(r => ({ ...r, mine: r.authorChannelId === myId }))
    return { threadId: item.id, videoId: s.videoId ?? '', channelId: s.channelId ?? '', canReply: s.canReply !== false,
      replyCount: Number(s.totalReplyCount ?? 0), ...top, id: top.id ?? item.id, mine: top.authorChannelId === myId,
      repliedByMe: replies.some(r => r.mine), replies }
  }

  /** 一个视频的评论区；只看自己频道的视频 */
  async function comments(videoId, { n = 20, order = 'time' } = {}) {
    if (!ID.test(String(videoId ?? ''))) throw new YouTubeError('视频 ID 不对（形如 dQw4w9WgXcQ）', 'YT_ARGS')
    const ch = await me()
    const v = await api('videos', { part: 'snippet', id: videoId })
    const video = v.items?.[0]
    if (!video) throw new YouTubeError('找不到这个视频（可能是私享/已删除）', 'YT_HTTP')
    if (video.snippet?.channelId !== ch.id) throw new YouTubeError('这个视频不是你自己频道发的；阶段 1 只看自己频道的评论区', 'YT_SCOPE')
    const j = await api('commentThreads', { part: 'snippet,replies', videoId, maxResults: String(Math.min(100, Math.max(1, n))),
      order: order === 'relevance' ? 'relevance' : 'time', textFormat: 'plainText' })
    return { video: { id: videoId, title: video.snippet?.title ?? '' }, threads: (j.items ?? []).map(it => thread(it, ch.id)) }
  }

  /** 整个频道的评论收件箱（所有视频，按时间倒序） */
  async function inbox({ n = 20, unreplied = false } = {}) {
    const ch = await me()
    const j = await api('commentThreads', { part: 'snippet,replies', allThreadsRelatedToChannelId: ch.id, maxResults: String(Math.min(100, Math.max(1, n))),
      order: 'time', textFormat: 'plainText' })
    const threads = (j.items ?? []).map(it => thread(it, ch.id))
    return unreplied ? threads.filter(t => !t.mine && !t.repliedByMe && t.canReply) : threads
  }

  /** 一整条楼：顶层评论 + 全部回复（回复后回读核查用） */
  async function threadOf(threadId) {
    const tid = String(threadId ?? '').split('.')[0]
    if (!ID.test(tid)) throw new YouTubeError('评论 ID 不对', 'YT_ARGS')
    const ch = await me()
    const t = await api('commentThreads', { part: 'snippet', id: tid, textFormat: 'plainText' })
    const item = t.items?.[0]
    if (!item) throw new YouTubeError('找不到这条评论（可能已被删除）', 'YT_HTTP')
    if (item.snippet?.channelId !== ch.id) throw new YouTubeError('这条评论不在你自己频道的视频下', 'YT_SCOPE')
    const replies = []
    let pageToken
    for (let page = 0; page < 5; page += 1) {
      const r = await api('comments', { part: 'snippet', parentId: tid, maxResults: '100', textFormat: 'plainText', ...(pageToken ? { pageToken } : {}) })
      replies.push(...(r.items ?? []).map(plain).map(x => ({ ...x, mine: x.authorChannelId === ch.id })))
      pageToken = r.nextPageToken
      if (!pageToken) break
    }
    return { ...thread(item, ch.id), replies, repliedByMe: replies.some(r => r.mine) }
  }

  const replied = () => readJson(REPLIED, { byComment: {} })
  const saveReplied = fn => locked(REPLIED + '.lock', () => { const o = replied(); o.byComment ??= {}; const r = fn(o); writeJson(REPLIED, o); return r })

  /**
   * 回复一条评论。commentId 可以是顶层评论（= 楼 ID），也可以是楼里的某条回复（形如 楼ID.回复ID）；
   * YouTube 只有两层，回复楼中楼时 parentId 仍是楼 ID（这是平台规则，不是 bug）。
   */
  async function reply(commentId, message, { go = false } = {}) {
    const cid = String(commentId ?? '').trim()
    if (!/^[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]+)?$/.test(cid)) throw new YouTubeError('评论 ID 不对（从 yt comments / yt inbox 的输出里复制）', 'YT_ARGS')
    const text = String(message ?? '').trim()
    if (!text) throw new YouTubeError('回复内容不能为空', 'YT_ARGS')
    if ([...text].length > MAX_REPLY_CHARS) throw new YouTubeError(`回复太长（上限 ${MAX_REPLY_CHARS} 字）`, 'YT_ARGS')
    const prior = replied().byComment?.[cid]
    if (prior) {
      throw new YouTubeError(prior.status === 'sent'
        ? `这条评论已经回过了（${prior.at}，回复 ID ${prior.replyId}）；同一条只回一次`
        : `这条评论上次的回复结果不确定（${prior.at}）。先用 yt thread ${cid.split('.')[0]} 核查：没发出去再运行 yt replied --forget ${cid}`, 'YT_DUP')
    }
    const ch = await me()
    const threadId = cid.split('.')[0]
    const t = await api('commentThreads', { part: 'snippet', id: threadId, textFormat: 'plainText' })
    const item = t.items?.[0]
    if (!item) throw new YouTubeError('找不到这条评论（可能已被删除）', 'YT_HTTP')
    if (item.snippet?.channelId !== ch.id) throw new YouTubeError('这条评论不在你自己频道的视频下；按规则不回复', 'YT_SCOPE')
    if (item.snippet?.canReply === false) throw new YouTubeError('这条评论不允许回复（视频关闭了评论或评论被限制）', 'YT_SCOPE')
    let target = plain(item.snippet?.topLevelComment)
    if (cid !== threadId) {
      const c = await api('comments', { part: 'snippet', id: cid, textFormat: 'plainText' })
      if (!c.items?.[0]) throw new YouTubeError('找不到这条回复（可能已被删除）', 'YT_HTTP')
      target = plain(c.items[0])
    }
    if (target.authorChannelId === ch.id) throw new YouTubeError('这是你自己发的评论，不回复自己', 'YT_SCOPE')
    const request = { method: 'POST', endpoint: API + 'comments?part=snippet', body: { snippet: { parentId: threadId, textOriginal: text } } }
    const result = { commentId: cid, threadId, videoId: item.snippet?.videoId ?? '', target: { author: target.author, text: target.text }, request }
    if (!go) return { ...result, dry: true }
    await saveReplied(o => {
      if (o.byComment[cid]) throw new YouTubeError('这条评论刚被另一个进程回复过，本次不发', 'YT_DUP')
      o.byComment[cid] = { at: new Date(now()).toISOString(), status: 'pending', threadId }
    })
    let posted
    try {
      posted = await api('comments', { part: 'snippet' }, { method: 'POST', body: request.body })
    } catch (e) {
      // 确定没发出去 → 释放判重记录；结果不确定 → 留着 unknown，禁止自动重发
      await saveReplied(o => { if (e.code === 'YT_UNCERTAIN') o.byComment[cid].status = 'unknown'; else delete o.byComment[cid] })
      throw e
    }
    await saveReplied(o => { o.byComment[cid] = { ...o.byComment[cid], status: 'sent', replyId: posted.id ?? null } })
    return { ...result, dry: false, replyId: posted.id ?? null, text: posted.snippet?.textDisplay ?? text }
  }

  async function forget(commentId) {
    return saveReplied(o => { const had = !!o.byComment[commentId]; delete o.byComment[commentId]; return had })
  }

  // ── 上传视频（2026-10-26）─────────────────────────────────────────────
  //   · 只在主人给出指令时才跑（她的提示里写死：不许主动上传）；必须显式 --dry / --go
  //   · 默认公开（主人定的）；定时发布按官方规则必须先私享，到点自动公开
  //   · 断点续传：会话地址记在 youtube-uploads.json，中断后再跑同一条命令从断点接着传
  //   · 同一个文件传成功后不许再传；结果不确定（最后一块发出后断网）时禁止自动重传
  const UPLOADS = file('youtube-uploads.json')
  const uploads = () => readJson(UPLOADS, { byFile: {} })
  const saveUploads = fn => locked(UPLOADS + '.lock', () => { const o = uploads(); o.byFile ??= {}; const r = fn(o); writeJson(UPLOADS, o); return r })
  const fingerprint = (abs, st) => crypto.createHash('sha256').update(`${process.platform === 'win32' ? abs.toLowerCase() : abs}|${st.size}|${Math.floor(st.mtimeMs)}`).digest('hex').slice(0, 24)

  /** 校验参数、拼出要发给 YouTube 的元数据（dry 和 go 共用，dry 不发任何写请求） */
  function uploadPlan(input) {
    const abs = path.resolve(String(input.file ?? ''))
    let st
    try { st = fs.statSync(abs) } catch { throw new YouTubeError(`找不到视频文件：${abs}`, 'YT_ARGS') }
    if (!st.isFile() || st.size <= 0) throw new YouTubeError(`不是有效的视频文件：${abs}`, 'YT_ARGS')
    if (st.size > 256 * 1024 ** 3) throw new YouTubeError('视频超过 YouTube 上限 256GB', 'YT_ARGS')
    const mime = VIDEO_TYPES[path.extname(abs).toLowerCase()]
    if (!mime) throw new YouTubeError(`不认识的视频格式：${path.extname(abs) || '（无扩展名）'}（支持 ${Object.keys(VIDEO_TYPES).join(' ')}）`, 'YT_ARGS')
    const title = String(input.title ?? '').trim()
    if (!title) throw new YouTubeError('要给 --title（标题）', 'YT_ARGS')
    if ([...title].length > 100 || /[<>]/.test(title)) throw new YouTubeError('标题要 1–100 字，且不能有 < >', 'YT_ARGS')
    const description = String(input.description ?? '')
    if (Buffer.byteLength(description, 'utf8') > 5000 || /[<>]/.test(description)) throw new YouTubeError('简介要 ≤5000 字节，且不能有 < >', 'YT_ARGS')
    const tags = (Array.isArray(input.tags) ? input.tags : String(input.tags ?? '').split(/[,，]/)).map(s => String(s).trim()).filter(Boolean)
    if (tags.join(',').length > 500) throw new YouTubeError('标签合计要 ≤500 字', 'YT_ARGS')
    const categoryId = String(input.category ?? '22')
    if (!/^\d+$/.test(categoryId)) throw new YouTubeError('--category 要是数字分类 ID（默认 22 = 人物与博客）', 'YT_ARGS')
    let privacy = input.privacy === undefined ? 'public' : String(input.privacy)
    if (!['public', 'unlisted', 'private'].includes(privacy)) throw new YouTubeError('--privacy 只能是 public / unlisted / private', 'YT_ARGS')
    let publishAt = null
    if (input.publishAt) {
      const t = Date.parse(String(input.publishAt))
      if (!Number.isFinite(t) || t <= now()) throw new YouTubeError('--publish-at 要是将来的时间，例如 2026-11-01T20:00:00+08:00', 'YT_ARGS')
      if (input.privacy !== undefined && privacy !== 'private') throw new YouTubeError('定时发布时视频必须先私享（YouTube 规定），到点自动公开；去掉 --privacy 或改成 private', 'YT_ARGS')
      privacy = 'private'
      publishAt = new Date(t).toISOString()
    }
    let thumbnail = null
    if (input.thumbnail) {
      thumbnail = path.resolve(String(input.thumbnail))
      const type = IMAGE_TYPES[path.extname(thumbnail).toLowerCase()]
      let ts
      try { ts = fs.statSync(thumbnail) } catch { throw new YouTubeError(`找不到封面文件：${thumbnail}`, 'YT_ARGS') }
      if (!type) throw new YouTubeError('封面只能是 JPG / PNG', 'YT_ARGS')
      if (ts.size > 2 * 1024 * 1024) throw new YouTubeError('封面要 ≤2MB（YouTube 的要求）', 'YT_ARGS')
    }
    const playlistId = input.playlist ? String(input.playlist).trim() : null
    if (playlistId && !ID.test(playlistId)) throw new YouTubeError('--playlist 要是播放列表 ID（形如 PLxxxx）', 'YT_ARGS')
    const resource = {
      snippet: { title, description, tags, categoryId },
      status: { privacyStatus: privacy, selfDeclaredMadeForKids: input.kids === true, ...(publishAt ? { publishAt } : {}) },
    }
    return { abs, size: st.size, mime, key: fingerprint(abs, st), resource, thumbnail, playlistId }
  }

  async function authed(url, init, what) {
    const send = async tok => {
      try { return await transport(url, { redirect: 'manual', ...init, headers: { authorization: 'Bearer ' + tok, ...init.headers } }) }
      catch (e) { throw Object.assign(new YouTubeError(`${what}网络中断：${e.cause?.code ?? e.message}`, 'YT_NET'), { network: true }) }
    }
    let res = await send(await accessToken())
    if (res.status === 401) res = await send(await accessToken({ force: true }))
    return res
  }

  /** 问 YouTube 这个续传会话已经收到多少字节；返回 { done, offset, video } */
  async function uploadOffset(session, size) {
    const res = await authed(session, { method: 'PUT', headers: { 'content-range': `bytes */${size}`, 'content-length': '0' }, signal: AbortSignal.timeout(30000) }, '查询续传进度')
    if (res.status === 200 || res.status === 201) return { done: true, video: await res.json().catch(() => ({})) }
    if (res.status === 308) {
      const m = String(res.headers.get('range') ?? '').match(/bytes=0-(\d+)/)
      return { done: false, offset: m ? Number(m[1]) + 1 : 0 }
    }
    if (res.status === 404 || res.status === 410) return { expired: true }
    throw await failure(res, await res.json().catch(() => null), '续传查询')
  }

  async function upload(input, { go = false, onProgress = () => {} } = {}) {
    const plan = uploadPlan(input)
    const prior = uploads().byFile?.[plan.key]
    if (prior?.status === 'done') throw new YouTubeError(`这个文件已经传过了（${prior.at}，视频 https://youtu.be/${prior.videoId}）；同一个文件不重复发布`, 'YT_DUP')
    const ch = await me()
    const summary = { file: plan.abs, size: plan.size, channel: ch.title, ...plan.resource, thumbnail: plan.thumbnail, playlistId: plan.playlistId,
      resume: prior?.session ? true : false }
    if (!go) return { dry: true, ...summary }
    if (prior?.status === 'unknown') throw new YouTubeError(`这个文件上次上传的结果不确定（${prior.at}）。先到 YouTube Studio 看有没有这条；没有再运行 yt uploads --forget "${plan.abs}"`, 'YT_DUP')

    let session = prior?.session && now() - Date.parse(prior.at) < 6 * 86400000 ? prior.session : null
    let offset = 0, video = null
    if (session) {
      const st = await uploadOffset(session, plan.size)
      if (st.done) video = st.video
      else if (st.expired) session = null
      else offset = st.offset
    }
    if (!session && !video) {
      await reserve(0, 'upload')
      const init = await authed(UPLOAD + 'videos?' + new URLSearchParams({ uploadType: 'resumable', part: 'snippet,status' }), {
        method: 'POST', body: JSON.stringify(plan.resource), signal: AbortSignal.timeout(60000),
        headers: { 'content-type': 'application/json; charset=UTF-8', 'x-upload-content-length': String(plan.size), 'x-upload-content-type': plan.mime },
      }, '创建上传会话')
      if (!init.ok) throw await failure(init, await init.json().catch(() => null), 'videos.insert')
      session = init.headers.get('location')
      if (!session) throw new YouTubeError('YouTube 没有返回上传地址', 'YT_HTTP')
      await saveUploads(o => { o.byFile[plan.key] = { at: new Date(now()).toISOString(), status: 'uploading', session, file: plan.abs, title: plan.resource.snippet.title } })
    }

    const fh = video ? null : await fs.promises.open(plan.abs, 'r')
    try {
      let errors = 0
      while (!video) {
        const end = Math.min(plan.size, offset + uploadChunk) - 1
        const buf = Buffer.alloc(end - offset + 1)
        await fh.read(buf, 0, buf.length, offset)
        let res
        try {
          res = await authed(session, { method: 'PUT', body: buf, signal: AbortSignal.timeout(300000),
            headers: { 'content-type': plan.mime, 'content-length': String(buf.length), 'content-range': `bytes ${offset}-${end}/${plan.size}` } }, '上传分块')
        } catch (e) {
          // 会话地址已落盘：再跑同一条命令会先问 YouTube 收到了多少（连最后一块到底到没到也问得出来），不会重复发布 ✓
          if (!e.network || ++errors > 5) throw new YouTubeError(`上传中断：${e.message}。再跑一次同一条命令会先向 YouTube 核对进度，再从断点接着传`, 'YT_NET')
          await sleep(Math.min(60000, 2000 * 2 ** errors))
          const st = await uploadOffset(session, plan.size)
          if (st.done) { video = st.video; break }
          if (st.expired) throw new YouTubeError('上传会话已过期，请重新运行（会从头传）', 'YT_NET')
          offset = st.offset
          continue
        }
        if (res.status === 200 || res.status === 201) { video = await res.json(); break }
        if (res.status === 308) {
          const m = String(res.headers.get('range') ?? '').match(/bytes=0-(\d+)/)
          offset = m ? Number(m[1]) + 1 : 0
          errors = 0
          onProgress(offset, plan.size)
          continue
        }
        if (res.status >= 500 && ++errors <= 5) {
          await sleep(Math.min(60000, 2000 * 2 ** errors))
          const st = await uploadOffset(session, plan.size)
          if (st.done) { video = st.video; break }
          offset = st.offset ?? offset
          continue
        }
        throw await failure(res, await res.json().catch(() => null), '上传分块')
      }
    } finally { await fh?.close() }
    if (!video?.id) {
      await saveUploads(o => { if (o.byFile[plan.key]) o.byFile[plan.key].status = 'unknown' })
      throw new YouTubeError('上传完成但没拿到视频 ID，已标记为结果不确定；请到 YouTube Studio 核查', 'YT_UNCERTAIN')
    }
    onProgress(plan.size, plan.size)
    await saveUploads(o => { o.byFile[plan.key] = { at: new Date(now()).toISOString(), status: 'done', videoId: video.id, file: plan.abs, title: plan.resource.snippet.title } })

    // 视频已经发出去了：封面 / 播放列表失败只算警告，不算整次失败
    const warnings = []
    if (plan.thumbnail) {
      try {
        await reserve(50, 'write')
        const img = fs.readFileSync(plan.thumbnail)
        const res = await authed(UPLOAD + 'thumbnails/set?' + new URLSearchParams({ videoId: video.id, uploadType: 'media' }), {
          method: 'POST', body: img, signal: AbortSignal.timeout(60000),
          headers: { 'content-type': IMAGE_TYPES[path.extname(plan.thumbnail).toLowerCase()], 'content-length': String(img.length) },
        }, '设置封面')
        if (!res.ok) throw await failure(res, await res.json().catch(() => null), 'thumbnails.set')
      } catch (e) {
        warnings.push(`封面没设上：${e.message}${/forbidden|403/.test(e.message) ? '（自定义封面要先在 YouTube 验证频道手机号）' : ''}`)
      }
    }
    if (plan.playlistId) {
      try {
        await api('playlistItems', { part: 'snippet' }, { method: 'POST', kind: 'write', units: 50,
          body: { snippet: { playlistId: plan.playlistId, resourceId: { kind: 'youtube#video', videoId: video.id } } } })
      } catch (e) { warnings.push(`没加进播放列表：${e.message}`) }
    }
    return { dry: false, videoId: video.id, url: `https://youtu.be/${video.id}`, privacy: video.status?.privacyStatus ?? plan.resource.status.privacyStatus,
      publishAt: video.status?.publishAt ?? plan.resource.status.publishAt ?? null, title: video.snippet?.title ?? plan.resource.snippet.title, warnings }
  }

  async function forgetUpload(file) {
    const abs = path.resolve(String(file ?? ''))
    const norm = p => process.platform === 'win32' ? p.toLowerCase() : p
    return saveUploads(o => {
      const keys = Object.keys(o.byFile).filter(k => norm(o.byFile[k].file ?? '') === norm(abs) && o.byFile[k].status !== 'done')
      for (const k of keys) delete o.byFile[k]
      return keys.length
    })
  }

  return { loadClient, saveClient, login, logout, status, me, myVideos, comments, inbox, thread: threadOf, reply, replied, forget, api, upload, uploads, forgetUpload }
}
