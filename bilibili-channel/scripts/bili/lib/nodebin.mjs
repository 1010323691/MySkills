// 子进程用哪个 node：独立运行时就是当前这个 node（旧版要在 DSH 的 Electron 里找真 node，这里不需要了）
export const NODE_EXE = process.execPath
export const NODE_ENV = {}
export const isRealNode = (p = NODE_EXE) => p === NODE_EXE
