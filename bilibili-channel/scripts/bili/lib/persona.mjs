// 人设提示词：配置里的 persona 段（名字 / 怎么称呼用户 / 自称 / 补充）+ 人设文件全文，拼成一段给模型读
//
//   `bili persona` 打印这段提示词；值守回复、发动态、私信、去别人评论区发言前都先读它
//   身份字段在前，人设文件在后；两者冲突时以人设文件为准（和旧版 DSH 插件的「身份注入」一致）
import fs from 'node:fs'

export function personaPrompt(cfg) {
  const p = cfg.persona ?? {}
  const bits = []
  if (p.name) bits.push(`你是「${p.name}」`)
  if (p.ownerTitle) bits.push(`称用户「${p.ownerTitle}」`)
  if (p.selfClaim) bits.push(`自称「${p.selfClaim}」`)
  const notes = (Array.isArray(p.notes) ? p.notes : []).map(s => String(s).trim()).filter(Boolean)

  let text = '', title = null, problem = null
  if (p.file) {
    try {
      // 填写提示是 HTML 注释，不进提示词
      text = fs.readFileSync(p.file, 'utf8').replace(/<!--[\s\S]*?-->/g, '').replace(/\n{3,}/g, '\n\n').trim()
      title = (text.match(/^#\s+(.+)$/m)?.[1] ?? '').trim() || null
      // /bili-init 生成的空模板（只有标题、引言和没填的「名字：」这类行）不算人设
      const filled = text.split(/\r?\n/).filter(l => l.trim() && !/^\s*[#>]/.test(l) && !/^\s*-\s*[^：:]{1,12}[：:]\s*$/.test(l))
      if (!filled.length) { problem = `人设还没写：${p.file} 还是空模板，跑 /bili-init 和用户一起创建`; text = '' }
    } catch { problem = `人设文件读不到：${p.file}` }
  }

  const parts = []
  if (bits.length) parts.push(`［身份］${bits.join('，')}。以此为准，别用别的称呼。`)
  if (notes.length) parts.push(`［补充］\n${notes.map(n => `- ${n}`).join('\n')}`)
  if (text) parts.push(`［人设］以下是你专属的设定，说话、写动态、选题都以它为准；与上面［身份］冲突时，以这一份为准：\n\n${text.slice(0, 20000)}`)

  const configured = bits.length > 0 || notes.length > 0 || !!p.file
  return {
    configured,
    loaded: configured && !problem,
    name: p.name || title || null,
    title, file: p.file || null, chars: text.length,
    problem: problem ?? (configured ? null : '配置里没填 persona，说话没有人设可依'),
    prompt: parts.join('\n\n'),
  }
}
