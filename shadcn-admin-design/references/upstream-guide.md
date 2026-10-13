# shadcn-admin 复用指南

查阅日期：2026-10-13。以下依据上游 `main` 的实际文件，分支会变化；使用时重新检查相关文件、依赖与许可证。这里是定位指南，不是已锁定的源码副本。

## 来源与边界

- [仓库](https://github.com/satnaing/shadcn-admin)、[演示站](https://shadcn-admin.netlify.app/)、[README](https://github.com/satnaing/shadcn-admin/blob/main/README.md)。
- 上游定位为后台 UI 集合，README 明确说明并非完整 starter。认证只有部分 Clerk 集成，示例 UI、数据和路由不能据此认定已有后端、权限控制或真实业务逻辑。
- 组件 / 布局可按需提取；新设计不等于复制整仓，现有优化不等于替换整个框架。
- [MIT 许可证](https://github.com/satnaing/shadcn-admin/blob/main/LICENSE)：复制源码或实质部分时保留 Sat Naing 版权和完整许可声明。此技能本身没有打包上游源码。

## 技术基线

[package.json](https://github.com/satnaing/shadcn-admin/blob/main/package.json) 核实的主要技术：React、TypeScript、Vite、Tailwind CSS v4、Radix / shadcn UI、TanStack Router / Query / Table、React Hook Form + Zod、Recharts、Zustand、Lucide。实际版本以目标项目和选定上游 ref 为准，不把最新版本当成强制升级要求。

[components.json](https://github.com/satnaing/shadcn-admin/blob/main/components.json)：`new-york` 风格、`slate` 基色、CSS variables、`rsc: false`，样式入口 `src/styles/index.css`，组件别名 `@/components/ui`，工具 `@/lib/utils`。移植到其他栈时检查别名、Provider、客户端边界、路由和样式兼容；不能直接假设适用于 Next.js、Vue 或其他 Router。

## 已核实的复用位置

| 需求 | 来源文件 / 位置 | 适配重点 |
|---|---|---|
| 管理框架 | [authenticated-layout.tsx](https://github.com/satnaing/shadcn-admin/blob/main/src/components/layout/authenticated-layout.tsx) | SearchProvider、LayoutProvider、SidebarProvider、AppSidebar、Outlet 和侧栏 cookie；名称不代表已完成服务端鉴权 |
| 导航与团队入口 | [sidebar-data.ts](https://github.com/satnaing/shadcn-admin/blob/main/src/components/layout/data/sidebar-data.ts) | 按业务换导航、团队和用户数据，移除无关演示入口；导航隐藏不能代替权限控制 |
| 仪表盘 | [dashboard/index.tsx](https://github.com/satnaing/shadcn-admin/blob/main/src/features/dashboard/index.tsx) | Header / Main、指标卡、Tabs、Overview 和 RecentSales；有 disabled 演示入口，需明确实际交互 |
| 数据管理列表 | [tasks-table.tsx](https://github.com/satnaing/shadcn-admin/blob/main/src/features/tasks/components/tasks-table.tsx) | TanStack Table、工具栏、分页、批量操作、URL 查询状态与 useTableUrlState；移植要一并核对 columns、schema、筛选字段和路由 search 配置 |
| 全站视觉 tokens | [theme.css](https://github.com/satnaing/shadcn-admin/blob/main/src/styles/theme.css) | `:root`、`.dark`、`@theme inline`；背景、前景、卡片、primary、ring、chart、sidebar 与 radius 成套适配 |
| 全局样式 | [index.css](https://github.com/satnaing/shadcn-admin/blob/main/src/styles/index.css) | Tailwind v4、tw-animate-css、dark variant、基础层；包含滚动锁定覆盖与手机输入字号规则，不能不加判断复制到其他栈 |

导航还显示 Tasks、Apps、Chats、Users、Auth、Errors、Settings 等页面模式。实现相关功能时再查相应 `src/features/` 和路由文件，不能根据入口名字推定所有功能已经完整。

## 组件更新陷阱

README 指出部分 UI 经过定制；先检查目标项目实际差异再更新，不自动运行 shadcn CLI 覆盖：

- 普通修改：`scroll-area`、`sonner`、`separator`。
- RTL 修改：`alert-dialog`、`calendar`、`command`、`dialog`、`dropdown-menu`、`select`、`table`、`sheet`、`sidebar`、`switch`。

需要更新时人工合并必要差异，保留已有功能与方向支持。中文场景可选合适字体回退，不能因为不需要 RTL 就清除其他定制。

## 取用顺序

先只读现有项目 → 定位需要的上游模式 → 检查源码依赖和样式 → 制作独立预览 → 获得具体批准 → 按需移植并记录实际 ref/commit 与许可。网络无法访问时说明未核实内容，使用本地已知资源设计，不假装取得最新源码。
