---
name: claude-terminal-workbench
description: 在 Ubuntu 上完整部署、复刻、检查或维护已固化的 Claude 米白 Ghostty + tmux 工作台，包含 Maple Mono 中文图标字体、左侧辅助区与右侧主工作区、项目会话和搜索工具。用于复刻这套既定终端环境；普通 Shell 命令和其他风格的终端设计不需要此技能。
---

# Claude Terminal Workbench

将用户已经选定的工作台完整部署到目标电脑。复用本技能内的配置和脚本，不依靠回忆重新生成一套近似配置。

## 固定的产品选择

- Ghostty + tmux；Claude 暖米白，深灰正文与陶土橙点缀。
- **左侧约 30% 为实时文件/Git 概况，右侧约 70% 为主工作区。** 保持这个顺序。
- Maple Mono Normal NF CN；Bash + Starship，短两行提示符。
- fzf、zoxide、eza、bat、fd、ripgrep；Lazygit 和 bottom 按需打开。
- Work、Dev、Studio 入口；项目使用命名 tmux 会话。

用户明确提出新偏好时，以用户当前要求为准。`assets/home/` 是配置模板；`assets/manifest.json` 记录已验证系统、模板校验值和固定发布资产。默认经过验证的系统是 Ubuntu 26.04 x86_64，字体 v7.9，bottom 0.14.9。系统包由目标发行版 apt 安装，安装版本会随其软件源更新，不承诺逐字节重建整个操作系统。

## 从检查到可用

所有命令中的 `<skill>` 是本 SKILL.md 所在目录；使用绝对路径。先确认用户要求的是部署、诊断、修改还是回退。

1. 运行 `python3 <skill>/scripts/workbench.py inspect`，检查系统、架构、Python 版本和当前配置；需要部署时再运行 `plan`。正常的“帮我复刻/配置”请求授权执行部署，按流程完成，不把普通文件备份和写入变成额外审批环节。
2. 在已验证的 Ubuntu 26.04 x86_64 上，运行：

   ```bash
   python3 <skill>/scripts/workbench.py install --with-deps --with-assets --reload
   ```

   脚本会安装 apt 依赖，下载并校验固定发布的字体和 bottom，按目标主目录渲染路径，备份改动文件，合并自己的 Bash 区块，生成统一主题并检查。系统认证让用户在终端或系统窗口中完成；不索取聊天密码。
3. 运行 `python3 <skill>/scripts/workbench.py doctor`。若失败，根据输出修正具体问题，不把安装命令已退出视为成功。不要重复运行已经失败的下载或安装而不先检查原因。
4. 打开新的 Ghostty / Claude Terminal Work，验证左辅助右主区、中文与图标、目录跟随、Ctrl+R、文件搜索、项目切换。用临时项目验证含空格路径、Dev、Git 和监控。临时 tmux 测试只能清理自己创建的会话或独立 socket。
5. 告知主入口、重要快捷键、备份位置、验证结论和剩余限制。如果远端主机未提供，完成 `ssh-work` 入口即可，说明尚未连接远端实测。

新电脑需要联网以取得 apt 包及固定发布资产；已有完整依赖时，可以省略 `--with-deps`、`--with-assets` 只恢复配置。裸环境安装前必须有 Python 3.11+；缺少 Python 时先使用系统包安装它。

## 兼容与运行中的工作

- 对其他发行版、旧 Ubuntu 或其他架构，先解释与已验证方案的差异，使用该系统的官方安装渠道适配；不要绕过脚本的支持范围后宣称原样支持。固定 bottom 下载是 x86_64，不能给 ARM 安装此二进制。
- 保留现有 CUDA、Python、PATH 和用户自己的初始化；Bash 区块合并而不是覆盖整份 `.bashrc`。不为复刻擅自切换登录 Shell。
- 不清空现有会话，不执行全局 `tmux kill-server`，不自动启动用户项目的服务或计算任务。重载配置不等于重启进程。
- Ghostty 直接启动 tmux 包装脚本，因此 Bash 手动加载 Ghostty integration。必须在 Starship 构建提示符之后运行 Ghostty 的 prompt hook；保留防重复注册逻辑。
- tmux 的 RGB 设置必须幂等。日常分屏由 tmux 管理，Ghostty 标签页用于连接上下文。远端保活要求远端 tmux，不能靠本地配置替代。
- Ghostty 1.3 不使用 `ghostty +ssh`。`ssh-work` 通过系统 ssh 连接远端 tmux；不修改未知主机和认证资料。

## 诊断、维护与回退

- 仅检查：`python3 <skill>/scripts/workbench.py doctor`。本机个性化修改会作为 drift 报告，先判断是否符合当前用户意图，不自动抹除。
- 调整本机颜色：编辑 `~/.config/terminal-workbench/palette.toml`，运行 `terminal-theme`；Ghostty 重新加载，新 Shell/工具读取更新。字体、目录与快捷键以实际配置为准。
- 完整回退最近一次脚本部署：`python3 <skill>/scripts/workbench.py rollback`，或用 `--backup <journal目录>` 指定版本。它会在文件已被后续修改时停止以保护这些修改。回退只恢复配置，不卸载依赖或恢复运行中任务的内存状态。
- 要把新的用户偏好变为下一次复刻的默认值，修改技能的模板和语义颜色源，重新生成模板哈希并增加 manifest 版本，再做隔离部署检查。修改本机配置不会自动更新技能模板。
- 发布 Skill 或推送 Git 仓库仅在用户明确要求时进行；本技能不包含用户 SSH 凭据、历史记录或完整个人 `.bashrc`。

## 可移植性自检

修改部署脚本时，使用 `--home <隔离目录> --staging` 测试配置安装、重复安装和回退。该模式不执行系统安装、联网下载或 live reload。至少检查：旧 Bash 区块外内容与权限保留；目标用户名/路径被正确渲染；第二次安装无改动；有后续改动时回退会保护它；无改动时回退恢复原内容。

这个 Skill 是可运行的工作流包，不只是风格提示词。成功标准是目标机器真实可用，不是产出一份看起来相似的配置文本。
