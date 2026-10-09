# 合并队列与自动合并

当 `gh pr merge` 返回「已加入合并队列」，或 PR 上已有自动合并（`autoMergeRequest` 非空）时读取。核心风险：这两者都是**异步**合并，`--match-head-commit` 只校验调用那一刻的 HEAD，之后有人推送新提交时，异步安排未必随之失效——这会让未经审核的版本进入主干。

## 两阶段检查

- **入队前**：PR HEAD 的检查与入队要求必须满足（第 5.1 节门禁）。不要求尚未生成的队列检查在入队前通过。
- **入队后**：仓库保护会在 `merge_group` 临时提交上运行队列检查，由它把关。队列检查不能替代对 PR HEAD 的独立审核。

## 入队前核实保护

入队前确认仓库对「HEAD/base 变化」的出队/失效保护能维持本轮审核门禁（例如分支保护要求新推送后重新检查、或规则会让 PR 出队）。无法确认时，不新增异步合并安排，报告缺少的保护证据，交用户决定。

## 入队后跟踪

- 入队不等于已合并：持续用 `gh pr view <N> --repo <R> --json state,mergedAt,headRefOid` 跟踪，直到 `MERGED`。
- HEAD 或 base 变化 → 旧 CLEAR 失效。确认 PR 已被移出队列；未自动移出就用实际支持的方式（GitHub 网页或 GraphQL `dequeuePullRequest`）移出，再对新 HEAD 重新审核。不要编造不存在的 CLI 出队选项。
- `gh pr merge --disable-auto` 只撤销自动合并，**不等于**移出合并队列。

## 自动合并

- 不默认启用 `--auto`，也不能用自动合并去「等」尚未满足的审核/CI 门禁。
- PR 上已有、与本轮版本门禁冲突的自动合并：在授权范围内 `gh pr merge <N> --repo <R> --disable-auto` 并记录；无权限则报告阻塞。

## 超时或交接时

- 本轮开启的、无法保证版本门禁的异步安排：撤销自动合并或移出队列，并核实结果。
- 本轮之前就存在的安排：不盲目取消，说明风险交用户处理。
- 无法撤销时明确报告「仍可能异步合并」，不声称已安全暂停或已完成。

## 参考

- [gh pr merge](https://cli.github.com/manual/gh_pr_merge)：`--match-head-commit`、`--auto`、`--disable-auto` 与合并队列行为。
- [GitHub 合并队列](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/merging-a-pull-request-with-a-merge-queue)：队列检查与出队。
- [GitHub 自动合并](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/automatically-merging-a-pull-request)：异步安排不能假定在所有新推送场景下自动失效。
