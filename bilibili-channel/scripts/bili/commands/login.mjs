// B站 登录（2026-10-27，替代旧版 DSH 设置页里的扫码 / 粘贴 cookie）
//
//   node bili.mjs login                 # 扫码登录：终端里画二维码，同时存一张 PNG；用 B站 App 扫码确认
//   node bili.mjs login status [--json] # 当前凭据是哪个号、能不能写（不打印 cookie）
//   node bili.mjs login cookie <文件>   # 手动导入：文件里是 {sessdata,bili_jct,buvid3} JSON，或浏览器复制的整段 Cookie
//   node bili.mjs login logout          # 删除本机凭据
//
// 凭据存在 <数据目录>/credentials.json（权限 600），永远不打印
import fs from 'node:fs'
import path from 'node:path'
import QRCode from 'qrcode'
import { credentialsPath, DATA_DIR } from '../lib/paths.mjs'

const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
const PASSPORT = 'https://passport.bilibili.com'
const args = process.argv.slice(2)
const sub = args[0] && !args[0].startsWith('--') ? args[0] : ''
const JSON_OUT = args.includes('--json')
const clean = v => String(v ?? '').replace(/^["'\s]+|["'\s]+$/g, '')

async function getJson(url, headers = {}) {
  const res = await fetch(url, { headers: { 'user-agent': UA, referer: 'https://www.bilibili.com/', ...headers }, signal: AbortSignal.timeout(15000) })
  return { res, j: await res.json().catch(() => ({})) }
}
const cookieOf = c => `SESSDATA=${c.sessdata}; bili_jct=${c.bili_jct}${c.buvid3 ? '; buvid3=' + c.buvid3 : ''}`

/** 用 nav 接口确认凭据属于哪个号 */
async function whoami(c) {
  const { j } = await getJson('https://api.bilibili.com/x/web-interface/nav', { cookie: cookieOf(c) })
  if (j.code !== 0 || !j.data?.isLogin) return null
  return { mid: String(j.data.mid), name: j.data.uname, level: j.data.level_info?.current_level ?? null, vip: j.data.vipStatus === 1 }
}

function save(c) {
  fs.mkdirSync(DATA_DIR, { recursive: true })
  const tmp = credentialsPath + '.tmp'
  fs.writeFileSync(tmp, JSON.stringify({ sessdata: c.sessdata, bili_jct: c.bili_jct, buvid3: c.buvid3 ?? '' }, null, 2) + '\n', { mode: 0o600 })
  fs.renameSync(tmp, credentialsPath)
}
function load() {
  try { const j = JSON.parse(fs.readFileSync(credentialsPath, 'utf8').replace(/^﻿/, '')); return { sessdata: clean(j.sessdata), bili_jct: clean(j.bili_jct), buvid3: clean(j.buvid3) } }
  catch { return null }
}
const hint = who => `  下一步：把配置里的 self.mid 填成 ${who.mid}（bili-setup 会帮你填）`

async function qrLogin() {
  const { j } = await getJson(PASSPORT + '/x/passport-login/web/qrcode/generate')
  const url = j.data?.url, key = j.data?.qrcode_key
  if (!url || !/^[A-Za-z0-9_-]{1,256}$/.test(String(key ?? ''))) throw new Error('二维码生成失败，稍后重试')
  const png = path.join(DATA_DIR, 'login-qr.png')
  fs.mkdirSync(DATA_DIR, { recursive: true })
  await QRCode.toFile(png, url, { width: 360, margin: 2 })
  console.log(await QRCode.toString(url, { type: 'terminal', small: true }))
  console.log(`用 B站 App 扫上面的二维码（或打开图片：${png}），在手机上点「确认登录」。最多等 3 分钟…`)
  const deadline = Date.now() + 180000
  let scanned = false
  try {
    while (Date.now() < deadline) {
      await new Promise(r => setTimeout(r, 2000))
      const u = new URL('/x/passport-login/web/qrcode/poll', PASSPORT)
      u.searchParams.set('qrcode_key', key)
      const { res, j: p } = await getJson(u)
      const code = p.data?.code
      if (code === 86101) continue
      if (code === 86090) { if (!scanned) console.log('已扫码，等你在手机上确认…'); scanned = true; continue }
      if (code === 86038) throw new Error('二维码过期了，重新运行 bili login')
      if (code !== 0) throw new Error(`无法识别登录状态（code=${code ?? p.code}）`)
      const values = {}
      for (const ck of res.headers.getSetCookie?.() ?? []) {
        const pair = ck.split(';', 1)[0], i = pair.indexOf('=')
        values[pair.slice(0, i).trim()] = pair.slice(i + 1).trim()
      }
      const c = { sessdata: values.SESSDATA, bili_jct: values.bili_jct, buvid3: values.buvid3 ?? '' }
      if (!c.sessdata || !c.bili_jct) throw new Error('登录成功但没拿到 SESSDATA / bili_jct，重新扫一次')
      if (!c.buvid3) {
        // 部分写接口要 buvid3：扫码响应不一定带，单独领一个
        const { j: f } = await getJson('https://api.bilibili.com/x/frontend/finger/spi').catch(() => ({ j: {} }))
        c.buvid3 = f.data?.b_3 ?? ''
      }
      save(c)
      const who = await whoami(c)
      console.log(who ? `✓ 已登录：${who.name}（mid ${who.mid}，Lv${who.level}）` : '✓ 凭据已保存，但没能确认账号；运行 bili login status 看看')
      if (who) console.log(hint(who))
      return
    }
    throw new Error('等了 3 分钟没人确认，重新运行 bili login')
  } finally { try { fs.unlinkSync(png) } catch {} }
}

function parseCookieFile(file) {
  const text = fs.readFileSync(path.resolve(file), 'utf8').replace(/^﻿/, '').trim()
  try {
    const j = JSON.parse(text)
    return { sessdata: clean(j.sessdata ?? j.SESSDATA), bili_jct: clean(j.bili_jct), buvid3: clean(j.buvid3) }
  } catch {
    const get = k => clean(text.match(new RegExp(`(?:^|;\\s*)${k}=([^;]+)`))?.[1])
    return { sessdata: get('SESSDATA'), bili_jct: get('bili_jct'), buvid3: get('buvid3') }
  }
}

try {
  if (!sub) await qrLogin()
  else if (sub === 'status') {
    const c = load()
    const who = c ? await whoami(c) : null
    const s = { file: credentialsPath, saved: !!c, loggedIn: !!who, account: who, canWrite: !!(c?.sessdata && c?.bili_jct), hasBuvid3: !!c?.buvid3 }
    if (JSON_OUT) console.log(JSON.stringify(s, null, 2))
    else {
      console.log(`凭据：${s.saved ? credentialsPath : '✗ 没有（运行 bili login 扫码）'}`)
      if (s.saved) console.log(`登录：${who ? `✓ ${who.name}（mid ${who.mid}，Lv${who.level}${who.vip ? '，大会员' : ''}）` : '✗ 凭据失效了（重新 bili login）'}`)
      if (s.saved) console.log(`写操作：${s.canWrite ? '✓ 有 bili_jct' : '✗ 缺 bili_jct，发不了评论 / 动态 / 私信'}${s.hasBuvid3 ? '' : ' · ⚠ 缺 buvid3，部分接口会被风控'}`)
    }
  } else if (sub === 'cookie') {
    const file = args[1]
    if (!file) throw new Error('用法：bili login cookie <文件>（JSON 或浏览器复制的整段 Cookie）')
    const c = parseCookieFile(file)
    if (!c.sessdata || !c.bili_jct) throw new Error('文件里没找到 SESSDATA 和 bili_jct')
    const who = await whoami(c)
    if (!who) throw new Error('这份 cookie 登录不了（过期或复制错了），没有保存')
    save(c)
    console.log(`✓ 已导入：${who.name}（mid ${who.mid}）。原文件里有登录凭据，导入后可以删掉`)
    console.log(hint(who))
  } else if (sub === 'logout') {
    try { fs.unlinkSync(credentialsPath); console.log('✓ 已删除本机凭据（B站 那边的登录设备可在「账号安全」里移除）') } catch { console.log('本来就没有凭据') }
  } else throw new Error('login 子命令：（空）扫码 / status / cookie <文件> / logout')
} catch (e) {
  console.error('✗ ' + e.message)
  process.exit(1)
}
