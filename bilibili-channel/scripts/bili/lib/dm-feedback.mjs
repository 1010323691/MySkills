import fs from 'node:fs'
import path from 'node:path'
import { DATA_DIR } from './paths.mjs'   // 2026-10-27：数据目录从配置读，不再写死 ~/.bili-ai
export function latestFeedback(last, owner, home=DATA_DIR, now=Date.now()) {
  let state={}
  try{state=JSON.parse(fs.readFileSync(path.join(home,'dm-await-state.json'),'utf8'))}catch{}
  const dm=state.owner===String(owner)&&owner ? Number(state.lastIncoming)*1000 : 0
  const previous=Date.parse(last)
  const valid=[previous,dm].filter(t=>Number.isFinite(t)&&t>0&&t<=now)
  return valid.length?new Date(Math.max(...valid)).toISOString():null
}
