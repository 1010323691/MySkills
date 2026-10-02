# book-to-skill — 书/文档 → Agent skill 转换器

> 安装方式见[仓库根 README](../README.md)（Claude 与 Codex 通用）。

## 用途

把一本书/一份文档（PDF、EPUB、DOCX、HTML、Markdown、纯文本、RTF、MOBI/AZW 需 Calibre）转换成结构化 agent skill：提取框架、心智模型、原则、技术与反模式，生成完整 skill（`SKILL.md` + `chapters/` + `glossary.md` + `patterns.md` + `cheatsheet.md`）。核心原则是"提取结构，而非写读后感"——产物是可反复使用的工具包，不是章节摘要集。

四种模式（按用户措辞自动路由）：

1. **Full Conversion**（默认）— 全量转换
2. **Analyze Only** — 只提取结构、出报告，不生成 skill 文件
3. **Generate from Prior Analysis** — 用已有分析笔记直接生成
4. **Update / Fold-in** — 把新源文件并入已有 skill

## 来源与本地修改

- 基于开源项目 [virgiliojr94/book-to-skill](https://github.com/virgiliojr94/book-to-skill)（MIT，见 [LICENSE.md](LICENSE.md)）；本目录是独立可用的副本，不含上游仓库的 `.git`、tests、docs 与 CI 配置。
- **本地修改**：新增 **Step 6.5 — 自动备份原文**：转换完成后把本次处理的源文件完整复制进生成 skill 的 `source/` 子目录（校验文件数一致、记录体积、超 1 GB 在报告中提示；Update/Fold-in 按增量合并），使生成 skill 在原文被移动/删除后依然自包含。同步修改 6 处：Full Conversion 的 Output 说明、生成 SKILL.md 模板（How to Use + Scope & Limits）、Step 10 完成报告、Update/Fold-in 第 3 步、Quality Rule 7 澄清、Step 11 发布 GitHub 时自动 `.gitignore` 排除 `source/`（原文不进发布仓库）。
- 将来升级：拉取上游新版本后把 Step 6.5 及相关修改重新套到 `SKILL.md` 上（修改集中、有注释可检索）。

## 依赖

- Python 3（`python3` 或 `py`）；PDF/EPUB/DOCX 等格式可能需装对应解析库，`extract.py --check` 可打印按格式的环境报告
- Calibre（仅 MOBI/AZW 需要）
- `gh` CLI（仅 Step 11 发布 GitHub 需要）
- 无二进制依赖；`SKILL.md` + `scripts/` + `tools/` + `book_to_skill/` 四部分须整体成目录安装（脚本按目录内相对路径互相解析）

## 使用方法

显式调用：`/book-to-skill <path-to-document-folder-or-glob>... [skill-name-slug]`（Codex 中在提示词里点名该 skill）。

- 转换整本书：`/book-to-skill D:\books\某书`
- 只要分析：加一句 "analyze only"
- 更新已有 skill：指向已有 skill 目录或 slug，附新源文件

流程自带：Step 2.5 成本预估（需确认）、Step 2.6 大书 REPL 式探针（不全量读原文）、Step 9.5 安全扫描（非零退出即停，须人工裁决）、Step 10 清理临时工作目录与完成报告。生成的 skill 默认写入宿主的个人 skills 目录（Claude Code 为 `~/.claude/skills/` 或跨宿主根 `~/.agents/skills/` + 软链）。

## 注意

- 生成质量依赖源文件质量；扫描器（`tools/scan_generated_skill.py`）是建议性的注入检查，通过不等于内容无风险——生成后首次加载前看一眼报告。
- 第三方版权书的 skill 不要公开发布（Step 11 有版权闸门：默认 private）。
- 临时工作目录按运行隔离（`book_skill_work-<pid>`），清理时只删本次运行报告的那个。
