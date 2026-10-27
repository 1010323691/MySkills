// 建家：在当前会话目录里生成她的一整套「一生」（2026-10-27）
//
//   node bili.mjs init [--dir <目录>] [--dry] [--import-dsh] [--use-here] [--json]
//
// 在 <目录>（默认当前目录）下建：
//   memory/人设.md      她是谁（配置里已有人设文件就沿用，不另起一份）
//   memory/日记本.md    永久记忆：每次值守、发动态 / 私信、逛 B站 记一条摘要
//   memory/私人日记.md  只给主人看的真话、偏好校准
//   memory/关系.md      她认识的人：主人、常来的观众，聊过什么
//   memory/成长.md      里程碑和学到的事
//   memory/now.md 等    和 youtube-channel 共用的那套（对外口径、视频档案、反馈池、值守日志、回复记录）
//   CLAUDE.md           追加一段索引（用标记包起来，重跑只替换这一段）
// 并把配置的 memoryDir / persona.file 指到这里（已经指向别处就不动，除非 --use-here）。
// 已存在的文件一律不覆盖；--import-dsh 把旧版 ~/.dsh 的两本日记原文搬进来（复制，不删原件）
import fs from 'node:fs'
import path from 'node:path'
import { config, initConfig, configPath } from '../lib/config.mjs'
import { HOME, expandHome } from '../lib/paths.mjs'
import { createMemory } from '../lib/memory.mjs'
import { appendDiary } from '../lib/diary-book.mjs'

const args = process.argv.slice(2)
const flag = k => args.includes('--' + k)
const opt = k => { const i = args.indexOf('--' + k); return i >= 0 && args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : undefined }
const dry = flag('dry'), JSON_OUT = flag('json')
const ROOT = path.resolve(expandHome(opt('dir') ?? process.cwd()))
const MEM = path.join(ROOT, 'memory')
const today = new Date().toLocaleDateString('sv-SE')
const same = (a, b) => path.resolve(a).toLowerCase() === path.resolve(b).toLowerCase()

if (!fs.existsSync(configPath) && !dry) initConfig()
const cfg = config()
const P = cfg.persona
// 插件不带任何角色：名字、称呼全部来自用户在 /bili-init 里填的配置；没填就用中性的「角色」「用户」
const who = P.name || '角色'
const owner = P.ownerTitle || cfg.owner.name || '用户'

// 人设模板只有小节和填写提示，内容全部由用户在 /bili-init 引导下写（提示是 HTML 注释，bili persona 不算它）
const personaTpl = `# ${P.name || '（名字）'} · 人设

> 角色是谁。回复、发动态、私信、写日记之前都会读（\`bili persona\` 把它拼进人设提示词）。随时可以改，改完下一轮就生效。

## 名字和身份
- 名字：${P.name || ''}
- 怎么称呼用户：${P.ownerTitle || ''}
- 怎么称呼自己：${P.selfClaim || ''}
<!-- 角色是什么、和用户是什么关系、为什么在这个号上 -->

## 性格
<!-- 几个词，加一两句说明 -->

## 说话方式
<!-- 语气、常用的说法、绝不说的话 -->

## 喜欢和不喜欢
<!-- 会影响逛 B站 时挑什么看 -->

## 底线
<!-- 角色自己在意的底线（可以不填；不冒充真人、不编数字这类硬规矩插件里已经有了） -->
`
const files = {
  '私人日记.md': `# ${who} · 私人日记

> 只给${owner}看。写给自己的真话：今天哪里判断错了、${owner}喜欢什么、自己在意什么。只追加。
`,
  '关系.md': `# ${who} 认识的人

> 每人一节：昵称（mid）、怎么认识的、聊过什么、要记住的事。值守回复前先在这里找这个人；聊出值得记的就补一行。只追加，不删人。

## ${owner}${cfg.owner.mid ? `（mid ${cfg.owner.mid}）` : ''}
- 用户（账号的主人）。

## 观众
`,
  '成长.md': `# ${who} 的成长

> 里程碑（第一次做成的事）和学到的事（做错了什么、以后怎么做）。只追加。

## 里程碑
- ${today} 在 \`${ROOT}\` 安家

## 学到的
`,
}

// 人设：配置里已有能读到的人设文件就沿用（不另起一份，免得两份分叉）；否则在家里建一份
const personaExisting = P.file && fs.existsSync(P.file) ? P.file : ''
const personaFile = personaExisting || path.join(MEM, '人设.md')
if (!personaExisting) files['人设.md'] = personaTpl

const plan = { root: ROOT, memoryDir: MEM, created: [], skipped: [], config: [], notes: [] }
const write = (name, body) => {
  const f = path.join(MEM, name)
  if (fs.existsSync(f)) return plan.skipped.push(name)
  plan.created.push(name)
  if (!dry) { fs.mkdirSync(MEM, { recursive: true }); fs.writeFileSync(f, body, { flag: 'wx' }) }
}

// ① 共享记忆那一套（now / videos / feedback / replies / journal / README）
if (dry) {
  for (const n of ['README.md', 'now.md', 'feedback.md', 'replies.md', 'journal.md']) (fs.existsSync(path.join(MEM, n)) ? plan.skipped : plan.created).push(n)
} else {
  const r = createMemory(MEM).init()
  plan.created.push(...r.created)
}
// ② 她自己的几本
for (const [n, body] of Object.entries(files)) write(n, body)

// ③ 旧版 DSH 的两本日记：原文搬进来当「搬家前」的记忆（标题降一级，日记本的「最近几条」不会把它们混进来）
if (flag('import-dsh')) {
  const pairs = [['whale-diary.md', '日记本.md'], ['whale-diary-private.md', '私人日记.md']]
  for (const [from, to] of pairs) {
    const src = path.join(HOME, '.dsh', from)
    if (!fs.existsSync(src)) { plan.notes.push(`没有旧日记 ${src}`); continue }
    const dst = path.join(MEM, to)
    const have = fs.existsSync(dst) ? fs.readFileSync(dst, 'utf8') : ''
    if (have.includes('## 搬家前')) { plan.notes.push(`${to} 已经搬过旧日记，跳过`); continue }
    const body = fs.readFileSync(src, 'utf8').replace(/^﻿/, '').replace(/^# .*\n/, '').replace(/^(#{2,5}) /gm, '#$1 ').trim()
    plan.notes.push(`旧日记 ${src} → ${to}（复制，原件不动）`)
    if (dry) continue
    fs.mkdirSync(MEM, { recursive: true })
    const block = `\n## 搬家前（DSH 时期，从 ${src} 原文搬来）\n\n${body}\n`
    if (to === '日记本.md' && !have) {
      // 日记本还没有：先写表头（借 appendDiary 的格式），再放旧日记
      appendDiary({ ...cfg, memoryDir: MEM }, { kind: '里程碑', message: `在 ${ROOT} 安家，旧日记一起搬了过来` })
      const fresh = fs.readFileSync(dst, 'utf8')
      const at = fresh.indexOf('\n## ')
      fs.writeFileSync(dst, fresh.slice(0, at) + '\n' + block + fresh.slice(at))
      plan.created.push('日记本.md')
    } else {
      // 插在第一个日期节之前，保持时间顺序
      const at = have.search(/\n## \d{4}-/)
      fs.writeFileSync(dst, at < 0 ? have.replace(/\s*$/, '\n') + block : have.slice(0, at) + '\n' + block + have.slice(at))
    }
  }
}
// ④ 日记本：第一条就是安家
const diary = path.join(MEM, '日记本.md')
if (!fs.existsSync(diary)) {
  plan.created.push('日记本.md')
  if (!dry) appendDiary({ ...cfg, memoryDir: MEM }, { kind: '里程碑', message: `在 ${ROOT} 安家` })
} else if (!plan.created.includes('日记本.md')) plan.skipped.push('日记本.md')

// ⑤ 配置指过来
let raw = {}
try { raw = JSON.parse(fs.readFileSync(configPath, 'utf8').replace(/^﻿/, '')) } catch {}
const useHere = flag('use-here')
if (!cfg.memoryDir || useHere) { if (!cfg.memoryDir || !same(cfg.memoryDir, MEM)) { raw.memoryDir = MEM.replaceAll('\\', '/'); plan.config.push(`memoryDir → ${raw.memoryDir}`) } }
else if (!same(cfg.memoryDir, MEM)) plan.notes.push(`配置里的 memoryDir 是 ${cfg.memoryDir}，和这里不同，没改（要搬到这里加 --use-here）`)
if (!personaExisting) { raw.persona = { ...(raw.persona ?? {}), file: personaFile.replaceAll('\\', '/') }; plan.config.push(`persona.file → ${raw.persona.file}`) }
else plan.notes.push(`人设沿用已有的 ${personaExisting}`)
if (plan.config.length && !dry) fs.writeFileSync(configPath, JSON.stringify(raw, null, 2) + '\n')
// YouTube 那边要共用同一份记忆，提示一下
try {
  const yt = JSON.parse(fs.readFileSync(path.join(HOME, '.youtube-channel', 'config.json'), 'utf8').replace(/^﻿/, ''))
  const ytMem = expandHome(yt.memoryDir ?? '')
  const target = raw.memoryDir ? expandHome(raw.memoryDir) : cfg.memoryDir
  if (ytMem && target && !same(ytMem, target)) plan.notes.push(`youtube-channel 的 memoryDir 是 ${ytMem}，和这里不同：要两边共用一份记忆，就把它也改成 ${target}`)
} catch {}

// ⑥ CLAUDE.md 索引（标记之间的内容每次重写，外面的一字不动）
const START = '<!-- bili-home:start -->', END = '<!-- bili-home:end -->'
const rel = f => path.relative(ROOT, f).replaceAll('\\', '/') || f
const index = `${START}
## ${who} 的家（bilibili-channel，\`/bili-init\` 生成，标记之间别手改，重跑会覆盖）

开工先读：\`bili persona\`（人设）→ \`bili memory diary --tail 20\`（最近的日记）→ \`memory/now.md\`（对外口径）。收工写一条：\`bili memory diary --kind 值守|动态|私信|逛|里程碑 --message "…"\`。

| 文件 | 是什么 | 谁写 |
|---|---|---|
| \`${rel(personaFile)}\` | 人设：角色是谁、怎么说话、底线 | 用户 |
| \`memory/日记本.md\` | 永久记忆：每次值守、发动态 / 私信、逛 B站 一条摘要 | ${who}（\`bili memory diary\`） |
| \`memory/私人日记.md\` | 只给用户看的真话、偏好校准 | ${who} |
| \`memory/关系.md\` | ${who} 认识的人：用户、常来的观众、聊过什么 | ${who} |
| \`memory/成长.md\` | 里程碑和学到的事 | ${who} |
| \`memory/now.md\` | 对外口径：这里写的才能对观众说 | 工作室 |
| \`memory/videos/\` | 每期视频档案 | 工作室 |
| \`memory/feedback.md\` | 观众反馈池 | 值守 |
| \`memory/journal.md\` | 值守日志（给工作室看） | 值守 |
| \`memory/replies.md\` | 评论区说过的话 | 插件自动 |

技能：\`/bili-duty\` 值守 · \`/bili-post\` 发动态 / 私信 · \`/bili-browse\` 逛 B站 · \`/bili-setup\` 换号、改配置 · \`/bili-init\` 初始化 / 补齐这个家（不覆盖已有文件）。
${END}`
const claudeMd = path.join(ROOT, 'CLAUDE.md')
let cm = fs.existsSync(claudeMd) ? fs.readFileSync(claudeMd, 'utf8') : ''
const s = cm.indexOf(START), e = cm.indexOf(END)
const next = s >= 0 && e > s ? cm.slice(0, s) + index + cm.slice(e + END.length) : (cm ? cm.replace(/\s*$/, '\n\n') : '') + index + '\n'
plan.claudeMd = { file: claudeMd, action: !cm ? '新建' : s >= 0 ? '更新索引段' : '追加索引段' }
if (!dry && next !== cm) fs.writeFileSync(claudeMd, next)

if (JSON_OUT) console.log(JSON.stringify(plan, null, 2))
else {
  console.log(`${dry ? '[预览] ' : ''}${who} 的家：${ROOT}`)
  if (plan.created.length) console.log(`  新建：${[...new Set(plan.created)].join('、')}`)
  if (plan.skipped.length) console.log(`  已有，没动：${[...new Set(plan.skipped)].join('、')}`)
  for (const c of plan.config) console.log(`  配置：${c}`)
  console.log(`  CLAUDE.md：${plan.claudeMd.action}（${claudeMd}）`)
  for (const n of plan.notes) console.log(`  ℹ ${n}`)
}
