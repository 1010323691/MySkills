# PR 评论模板

执行第 2 节审核或第 3 节处理报告时读取。占位符须替换成真实记录，不能把模板当验证证据。

## 审核报告

```text
第 <N> 轮独立审核
PR：<URL>；base：<分支>；审核者：<本轮子 Agent 标识>
审核范围：<首轮完整 diff / 上轮SHA..本轮SHA；补充检查范围>
审核覆盖：<调用方、共享模块、数据流、配置及覆盖检查>
验证核查：<证据SHA、实际命令/结果、补充验证或未运行原因>

发现项：
[P<n>] <必须修 / 建议修 / 仅供参考>：<标题>
位置：<文件:行或具体代码范围>
事实与影响：<可核查事实、触发条件、影响>
建议：<修复方向 / 待裁决问题>

旧项核销与裁决：
[P<n>] <关闭：修复有效 / 关闭：接受反驳 / 未关闭：原因>
证据：<提交、diff、验证或处理评论链接>
用户延期裁定：<仅在存在直接裁定时记录其依据与范围>

Reviewed-Head: <完整HEAD SHA>
Verdict: <CLEAR 或 BLOCKED（必须修 N 项，建议修 M 项）>
```

没有发现时写「发现项：无」，不要保留虚构条目。问题编号全 PR 稳定且不重复；级别单独填写。

## 逐项处理报告

```text
第 <N> 轮处理报告
PR：<URL>；当前完整HEAD：<SHA>；对应审核评论：<链接>

处理状态：
| 编号 | 原级别 | 状态 | 修复提交/反驳理由与证据 | 独立核销/裁决链接 |
| ...  | ...    | ...  | ...                    | 尚待复审/实际链接 |

验证：<实际命令、结果、对应内容基线；轻量验证的适用理由>
待复审范围：<上轮SHA..当前SHA；未关闭项；有无base/范围变化>
用户裁定：<如有，记录直接裁定依据，不能用主 Agent 判断替代>
```

未得到独立核销时填「已修复，待核销」；提交反驳不等于已关闭。保留此前未关闭项。

## 发布与恢复

正文写入 UTF-8 临时文件，明确 repository/host 后通过 `gh pr comment --body-file` 发布，避免 shell 对反引号、变量和多行文本二次解释。发布成功记录 URL 后再清理临时文件。超时/网络错误导致结果未知时先读取 PR 评论查重，不盲目重复发布。

## CLI 依据

- [gh pr create](https://cli.github.com/manual/gh_pr_create)：显式指定仓库、base/head 和正文文件。
- [gh pr checks](https://cli.github.com/manual/gh_pr_checks)：检查详情；pending 有专门退出码，退出状态不能替代适用性和 SHA 核实。
- [gh pr merge](https://cli.github.com/manual/gh_pr_merge)：版本匹配参数及合并队列行为，仓库规则决定允许策略。
- [GitHub 合并队列](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/merging-a-pull-request-with-a-merge-queue)：队列检查及出队行为。
- [GitHub 自动合并](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/automatically-merging-a-pull-request)：异步安排不能假定在所有新推送场景自动失效。
