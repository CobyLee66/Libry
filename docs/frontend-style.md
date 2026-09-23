# 前端风格规范

前端 UI 改动必须遵循以下统一风格（agent 开发时必读）。前端位于 `libry/static/`（手写 Vue 3 + vendored 依赖，无构建步骤）。

- **图标**：统一 Feather 风格线性图标，一律经 `<icon name="...">` 组件渲染；新增图标只在 `libry/static/app.js` 的 `ICON_PATHS` 中添加 path（`viewBox="0 0 24 24"`、`fill="none"`、`stroke="currentColor"`、`stroke-width="2"`、圆角线帽线尾）。禁止引入其他图标库、图标字体或图片图标。
- **按钮体系**：文字按钮用 `.btn`，纯图标按钮用 `.icon-btn`（配 `title`/`aria-label`），图标按钮的计数用 `.icon-badge` 角标。
- **配色**：一律使用 `libry/static/style.css` `:root` 的 CSS 变量（`--bg/--card/--text/--muted/--border/--primary/--new/--unread`），不写死颜色值。
- **布局**：移动优先，窄屏断点 `640px`；正文/列表最大宽度 `860px`。手机端正文卡片无边框线，只留边距。阅读页 header 在窄屏分两行（第一行返回+标题常驻，第二行快捷操作按钮），向下滚动时按钮行自动收起、向上滚动恢复（`.actions-hidden` + `docBarHidden`），桌面端 `.topbar-row` 用 `display: contents` 抹平包装、保持单行。
- **表格**：正文表格超出宽度时在表格区域内横向滚动，单元格不换行（`white-space: nowrap`）。
- **i18n（界面文案）**：所有用户可见文案一律经 `t('key')` 取用（`i18n/core.js` 暴露的 `window.LibryI18n`），禁止在模板/JS 里硬编码语言文案；底层值（类型目录名、状态码、API 错误码）保持英文，展示层翻译。文案字典位于 `libry/static/i18n/<code>.js`（严格 JSON 字面量，`tests/test_i18n.py` 校验各语言 key 一致与模板引用无漏键）。占位符用 `{name}` 插值；可数文案可用 `{one, other}` 复数对象（`Intl.PluralRules` 按 `params.n` 选择）。语言偏好存 `localStorage['kb-lang']`（仅手动切换时写入，自动检测跟随浏览器，非中英环境回退 English）。
- **新增语言三步**：① `i18n/` 下新建 `<code>.js` 字典（含 `_meta.name` 本地语言名，key 集合与 en 完全一致）；② `index.html` 头部加一行 `<script src="/i18n/<code>.js">`；③ `i18n/core.js` 的 `detect()` 加浏览器语言到该 code 的映射。
- **静态资源缓存**：服务端对静态文件下发 `Cache-Control: no-cache`（ETag 未变更回 304）——发版后所有端立即拿到新代码，改前端不需要 bump 版本号参数。
