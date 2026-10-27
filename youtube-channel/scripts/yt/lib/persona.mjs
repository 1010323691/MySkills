// 人设提示词：配置里的 persona 段（名字 / 怎么称呼用户 / 自称 / 补充）+ 人设文件全文，拼成一段给模型读
//
//   配置：{ persona: { name, ownerTitle, selfClaim, file, notes: [] } }
//   `yt persona` 打印这段提示词；yt-duty 回复前、yt-publish 写简介前都先读它
//
// 和旧版 DSH 插件的「身份注入」一致：身份字段在前，人设文件在后；两者冲突时以人设文件为准
import fs from 'node:fs'

export function personaPrompt(cfg) {
  const p = cfg.persona ?? {}
  const bits = []
  if (p.name) bits.push(`You are "${p.name}"`)
  if (p.ownerTitle) bits.push(`you call the user "${p.ownerTitle}"`)
  if (p.selfClaim) bits.push(`you refer to yourself as "${p.selfClaim}"`)
  const notes = (Array.isArray(p.notes) ? p.notes : []).map(s => String(s).trim()).filter(Boolean)

  let text = '', title = null, problem = null
  if (p.file) {
    try {
      // 填写提示是 HTML 注释，不进提示词
      text = fs.readFileSync(p.file, 'utf8').replace(/<!--[\s\S]*?-->/g, '').replace(/\n{3,}/g, '\n\n').trim()
      title = (text.match(/^#\s+(.+)$/m)?.[1] ?? '').trim() || null
      // 空模板（只有标题、引言和没填的「名字：」这类行）不算人设
      const filled = text.split(/\r?\n/).filter(l => l.trim() && !/^\s*[#>]/.test(l) && !/^\s*-\s*[^：:]{1,12}[：:]\s*$/.test(l))
      if (!filled.length) { problem = `人设还没写：${p.file} 还是空模板，和用户一起写好（/bili-init 或 /yt-setup）`; text = '' }
    } catch { problem = `人设文件读不到：${p.file}` }
  }

  const parts = []
  if (bits.length) parts.push(`[Identity] ${bits.join('; ')}. Use exactly these.`)
  if (notes.length) parts.push(`[Notes]\n${notes.map(n => `- ${n}`).join('\n')}`)
  if (text) parts.push(`[Persona] Your own character sheet. Replies, journal entries and descriptions follow it; where it conflicts with [Identity] above, this sheet wins.\n\n${text.slice(0, 20000)}`)

  const configured = bits.length > 0 || notes.length > 0 || !!p.file
  return {
    configured,
    loaded: configured && !problem,
    name: p.name || title || null,
    title, file: p.file || null, chars: text.length,
    problem: problem ?? (configured ? null : '配置里没填 persona，回复没有人设可依'),
    prompt: parts.join('\n\n'),
  }
}
