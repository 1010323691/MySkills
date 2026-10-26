// 路径：插件自己的家目录和配置文件位置
//
//   插件家目录  $YOUTUBE_CHANNEL_HOME → ~/.youtube-channel
//   配置文件    $YOUTUBE_CHANNEL_CONFIG → <家目录>/config.json
//
// 令牌、账本、日志放在配置里的 dataDir（默认 <家目录>/data），见 config.mjs
import os from 'node:os'
import path from 'node:path'

/** 用户主目录（Windows 优先 USERPROFILE） */
export const HOME = process.env.USERPROFILE || process.env.HOME || os.homedir() || '.'

/** 配置里的路径允许写 ~ 开头 */
export const expandHome = p => {
  const s = String(p ?? '').trim()
  return s === '~' ? HOME : /^~[\\/]/.test(s) ? path.join(HOME, s.slice(2)) : s
}

export const APP_HOME = path.resolve(expandHome(process.env.YOUTUBE_CHANNEL_HOME || '~/.youtube-channel'))
export const configPath = path.resolve(expandHome(process.env.YOUTUBE_CHANNEL_CONFIG || path.join(APP_HOME, 'config.json')))
