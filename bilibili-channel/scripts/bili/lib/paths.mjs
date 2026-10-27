// 路径：插件自己的家目录、配置文件、数据目录（2026-10-27 从 dsh-bili-whale 迁出，不再依赖 DSH）
//
//   插件家目录  $BILIBILI_CHANNEL_HOME → ~/.bilibili-channel
//   配置文件    $BILIBILI_CHANNEL_CONFIG → <家目录>/config.json
//   数据目录    配置里的 dataDir → <家目录>/data      登录凭据、账本、缓存、请求日志
//   状态目录    <数据目录>/state                       日记、活动日志、截图（旧版放在 ~/.dsh 下的东西）
//
// 数据目录要在 config.mjs 之前就能算出来（很多模块顶层就拼路径），所以这里直接读一眼配置文件的 dataDir
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

/** 用户主目录（Windows 优先 USERPROFILE） */
export const HOME = process.env.USERPROFILE || process.env.HOME || os.homedir() || '.'

/** 配置里的路径允许写 ~ 开头 */
export const expandHome = p => {
  const s = String(p ?? '').trim()
  return s === '~' ? HOME : /^~[\\/]/.test(s) ? path.join(HOME, s.slice(2)) : s
}

export const APP_HOME = path.resolve(expandHome(process.env.BILIBILI_CHANNEL_HOME || '~/.bilibili-channel'))
export const configPath = path.resolve(expandHome(process.env.BILIBILI_CHANNEL_CONFIG || path.join(APP_HOME, 'config.json')))

function dataDirFromConfig() {
  try {
    const j = JSON.parse(fs.readFileSync(configPath, 'utf8').replace(/^﻿/, ''))
    if (j && typeof j.dataDir === 'string' && j.dataDir.trim()) return path.resolve(path.dirname(configPath), expandHome(j.dataDir))
  } catch {}
  return path.join(APP_HOME, 'data')
}

/** 数据目录：登录凭据、账本、缓存（旧版的 ~/.bili-ai） */
export const DATA_DIR = dataDirFromConfig()
/** 状态目录：日记、活动日志、截图（旧版的 ~/.dsh） */
export const STATE_DIR = path.join(DATA_DIR, 'state')
/** 旧名字保留给原有模块用 */
export const DSH_HOME = STATE_DIR
export const dshPath = (...parts) => path.join(STATE_DIR, ...parts)
export const dataPath = (...parts) => path.join(DATA_DIR, ...parts)
export const credentialsPath = dataPath('credentials.json')
