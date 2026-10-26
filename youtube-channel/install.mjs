#!/usr/bin/env node
// 安装：把脚本放到 ~/.youtube-channel/（装依赖），两个 skill 放到 ~/.claude/skills/，并把 skill 里的命令路径写成绝对路径
//   node install.mjs            # 安装 / 升级（不碰令牌、配置、共享记忆）
//   node install.mjs --dry      # 只打印要做什么
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const SRC = path.dirname(fileURLToPath(import.meta.url))
const HOME = os.homedir()
const DEST = process.env.YOUTUBE_CHANNEL_HOME || path.join(HOME, '.youtube-channel')
const SKILLS = path.join(HOME, '.claude', 'skills')
const dry = process.argv.includes('--dry')
const step = (msg, fn) => { console.log((dry ? '[dry] ' : '') + msg); if (!dry) fn() }

const scripts = path.join(DEST, 'scripts')
step(`复制脚本 → ${scripts}`, () => {
  fs.mkdirSync(DEST, { recursive: true })
  fs.cpSync(path.join(SRC, 'scripts'), scripts, { recursive: true, filter: p => !p.includes(`${path.sep}node_modules`) })
})
step('安装依赖（npm install）', () => {
  // 参数都是常量，整条交给 shell（Windows 上 npm 是 .cmd，必须经 shell 启动）
  const r = spawnSync('npm install --no-audit --no-fund --omit=dev', { cwd: path.join(scripts, 'yt'), stdio: 'inherit', shell: true })
  if (r.status !== 0) { console.error('npm install 失败'); process.exit(1) }
})
for (const name of ['channel-duty', 'channel-publish']) {
  const to = path.join(SKILLS, name)
  step(`安装 skill → ${to}`, () => {
    fs.mkdirSync(to, { recursive: true })
    const md = fs.readFileSync(path.join(SRC, 'skills', name, 'SKILL.md'), 'utf8')
      .replaceAll('<skill>/../../scripts', scripts.replaceAll('\\', '/'))
    fs.writeFileSync(path.join(to, 'SKILL.md'), md)
  })
}
console.log(`\n完成。下一步（第一次装才需要）：
  node "${path.join(scripts, 'yt', 'commands', 'yt.mjs')}" auth client <下载的客户端.json>
  node "${path.join(scripts, 'yt', 'commands', 'yt.mjs')}" auth login
详见 README 的「接通 YouTube」一节。`)
