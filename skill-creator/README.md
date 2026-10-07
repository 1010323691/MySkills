# skill-creator — 创建与迭代 skill（官方版）

> 安装方式见[仓库根 README](../README.md)（Claude 与 Codex 通用）。

## 用途

创建新 skill、修改与改进现有 skill、度量 skill 表现：写草稿 → 跑测试提示词 → 定性（eval-viewer 结果页）+ 定量（benchmark、方差分析）评审 → 迭代重写；另含 description 优化脚本，提升 skill 触发准确率。

## 来源

Anthropic 官方 `skill-creator` 完整副本（Apache-2.0，见 [LICENSE.txt](LICENSE.txt)），未做修改。含 `agents/`、`references/`、`scripts/`（`run_eval.py` / `run_loop.py` / `aggregate_benchmark.py` / `improve_description.py` / `quick_validate.py` 等）与 `eval-viewer/`（结果评审页生成）。

## 依赖

- Python 3（scripts 与 eval-viewer）
- 宿主能启动子 agent：evals 在带该 skill 的新会话里逐条跑测试提示词

## 使用方法

直接说「帮我做一个 X 的 skill」「给这个 skill 跑 evals」「优化 description 提升触发」。完整流程与迭代闭环见 `SKILL.md`。
