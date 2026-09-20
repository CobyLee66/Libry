# 前端风格规范

前端 UI 改动必须遵循以下统一风格（agent 开发时必读）。前端位于 `libry/static/`（手写 Vue 3 + vendored 依赖，无构建步骤）。

- **图标**：统一 Feather 风格线性图标，一律经 `<icon name="...">` 组件渲染；新增图标只在 `libry/static/app.js` 的 `ICON_PATHS` 中添加 path（`viewBox="0 0 24 24"`、`fill="none"`、`stroke="currentColor"`、`stroke-width="2"`、圆角线帽线尾）。禁止引入其他图标库、图标字体或图片图标。
- **按钮体系**：文字按钮用 `.btn`，纯图标按钮用 `.icon-btn`（配 `title`/`aria-label`），图标按钮的计数用 `.icon-badge` 角标。
- **配色**：一律使用 `libry/static/style.css` `:root` 的 CSS 变量（`--bg/--card/--text/--muted/--border/--primary/--new/--unread`），不写死颜色值。
- **布局**：移动优先，窄屏断点 `640px`；正文/列表最大宽度 `860px`。手机端正文卡片无边框线，只留边距。
- **表格**：正文表格超出宽度时在表格区域内横向滚动，单元格不换行（`white-space: nowrap`）。
- **静态资源缓存**：服务端对静态文件下发 `Cache-Control: no-cache`（ETag 未变更回 304）——发版后所有端立即拿到新代码，改前端不需要 bump 版本号参数。
