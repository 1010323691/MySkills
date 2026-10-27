#!/usr/bin/env node
// 安装：把脚本放到 ~/.bilibili-channel/（装依赖），五个 skill 放到 ~/.claude/skills/，并把 skill 里的命令路径写成绝对路径
//   node install.mjs            # 安装 / 升级（不碰登录凭据、配置、共享记忆）
//   node install.mjs --dry      # 只打印要做什么
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const SRC = path.dirname(fileURLToPath(import.meta.url))
const HOME = os.homedir()
// 和 scripts/bili/lib/paths.mjs 一样展开 ~，不然两边算出来的家目录不同
const expandHome = p => { const s = String(p).trim(); return s === '~' ? HOME : /^~[\\/]/.test(s) ? path.join(HOME, s.slice(2)) : s }
const DEST = path.resolve(expandHome(process.env.BILIBILI_CHANNEL_HOME || path.join(HOME, '.bilibili-channel')))
const SKILLS = path.join(HOME, '.claude', 'skills')
const dry = process.argv.includes('--dry')
const step = (msg, fn) => { console.log((dry ? '[dry] ' : '') + msg); if (!dry) fn() }

const scripts = path.join(DEST, 'scripts')
step(`复制脚本 → ${scripts}`, () => {
  fs.mkdirSync(DEST, { recursive: true })
  // 先整个删掉再复制：新版删掉的文件不会残留（这里只有代码和依赖，配置和数据不在 scripts/ 下）
  fs.rmSync(scripts, { recursive: true, force: true })
  fs.cpSync(path.join(SRC, 'scripts'), scripts, { recursive: true, filter: p => !p.includes(`${path.sep}node_modules`) })
  // 模板随插件升级；用户自己的 config.json 一律不碰
  fs.copyFileSync(path.join(SRC, 'config.template.json'), path.join(DEST, 'config.template.json'))
})
step('安装依赖（npm install）', () => {
  // 参数都是常量，整条交给 shell（Windows 上 npm 是 .cmd，必须经 shell 启动）
  const r = spawnSync('npm install --no-audit --no-fund --omit=dev', { cwd: path.join(scripts, 'bili'), stdio: 'inherit', shell: true })
  if (r.status !== 0) { console.error('npm install 失败'); process.exit(1) }
})
for (const name of ['bili-init', 'bili-setup', 'bili-duty', 'bili-post', 'bili-browse']) {
  const to = path.join(SKILLS, name)
  step(`安装 skill → ${to}`, () => {
    fs.mkdirSync(to, { recursive: true })
    const md = fs.readFileSync(path.join(SRC, 'skills', name, 'SKILL.md'), 'utf8')
      .replaceAll('<skill>/../../scripts', scripts.replaceAll('\\', '/'))
    fs.writeFileSync(path.join(to, 'SKILL.md'), md)
  })
}
console.log(`\n完成。下一步：在 Claude Code 里运行 /bili-setup，它会生成配置、逐项问你、再带你扫码登录 B站。
不用向导的话：
  node "${path.join(scripts, 'bili', 'bili.mjs')}" config init     # 生成 ${path.join(DEST, 'config.json')}，照 README 填写
详见 README 的「配置」和「登录 B站」两节。`)
