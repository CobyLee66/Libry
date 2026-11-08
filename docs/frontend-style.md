# 前端风格规范

前端 UI 改动必须遵循以下统一风格（agent 开发时必读）。前端位于 `libry/static/`（手写 Vue 3 + vendored 依赖，无构建步骤）。

- **图标**：统一 Feather 风格线性图标，一律经 `<icon name="...">` 组件渲染；新增图标只在 `libry/static/app.js` 的 `ICON_PATHS` 中添加 path（`viewBox="0 0 24 24"`、`fill="none"`、`stroke="currentColor"`、`stroke-width="2"`、圆角线帽线尾）。禁止引入其他图标库、图标字体或图片图标。
- **按钮体系**：文字按钮用 `.btn`，纯图标按钮用 `.icon-btn`（配 `title`/`aria-label`），图标按钮的计数用 `.icon-badge` 角标。
- **配色**：一律使用 `libry/static/style.css` `:root` 的 CSS 变量（`--bg/--card/--text/--muted/--border/--primary/--new/--unread`），不写死颜色值。
- **布局**：移动优先，窄屏断点 `640px`；正文/列表最大宽度 `860px`。手机端正文卡片无边框线，只留边距。阅读页 header 在窄屏分两行（第一行返回+标题常驻，第二行快捷操作按钮），向下滚动时按钮行自动收起、向上滚动恢复（`.actions-hidden` + `docBarHidden`）。显隐须按相对上次有效方向判定的累计位移切换，不能根据每个 scroll 事件的瞬时方向切换；顶部强制展开区与自动隐藏区之间需留缓冲，避免 Android 惯性/回弹事件在阈值附近反复触发。注意窄屏按钮行是挂在顶栏下沿的浮层（`position: absolute; top: 100%`），不占文档流高度——收起/展开不会改变页面总高，从而避免底部滚动时 scrollY 钳制被误判为上滑造成的收起⇄展开抖动；`.doc-body` 的 `padding-top` 需为展开的浮层让位。桌面端 `.topbar-row` 用 `display: contents` 抹平包装、保持单行。
- **表格**：正文表格超出宽度时在表格区域内横向滚动，单元格不换行（`white-space: nowrap`）。
- **i18n（界面文案）**：所有用户可见文案一律经 `t('key')` 取用（`i18n/core.js` 暴露的 `window.LibryI18n`），禁止在模板/JS 里硬编码语言文案；底层值（类型目录名、状态码、API 错误码）保持英文，展示层翻译。文案字典位于 `libry/static/i18n/<code>.js`（严格 JSON 字面量，`tests/test_i18n.py` 校验各语言 key 一致与模板引用无漏键）。占位符用 `{name}` 插值；可数文案可用 `{one, other}` 复数对象（`Intl.PluralRules` 按 `params.n` 选择）。语言偏好存 `localStorage['kb-lang']`（仅手动切换时写入，自动检测跟随浏览器，非中英环境回退 English）。
- **新增语言三步**：① `i18n/` 下新建 `<code>.js` 字典（含 `_meta.name` 本地语言名，key 集合与 en 完全一致）；② `index.html` 头部加一行 `<script src="/i18n/<code>.js">`；③ `i18n/core.js` 的 `detect()` 加浏览器语言到该 code 的映射。
- **静态资源缓存**：服务端对静态文件下发 `Cache-Control: no-cache`（ETag 未变更回 304）——发版后所有端立即拿到新代码，改前端不需要 bump 版本号参数。
- **离线能力**（`sw.js` + `offline.js` + `#/offline` 管理页）：请求策略必须保持**在线优先**（network-first），任何新资源类别不得默认 cache-first（`/raw/assets/` 素材与 vendor 是仅有的例外）；离线库按账户隔离（keyPath 含 user），登出必须清理；涉及请求策略或离线库结构改动先读 `docs/offline.md`。

## 中文输入法（IME）兼容规范

来源：语聊项目真机踩坑交接（Android WebView 组词丢字/落尾、`compositionend` 缺失、
`captureInput` 根因）。适用范围：Web 前端所有文本输入框 + `clients/` 壳内页面。

1. **Enter 提交守卫（必须）**：一切「回车触发提交/跳转」的输入框，处理器第一步必须是
   `if (e.isComposing || e.keyCode === 229) return;`——组词中的 Enter 是确认候选，
   不是提交意图；且确认分支之外**不要 preventDefault**（拦截会卡死候选确认）。
   参考实现：`app.js` 的 `tagDraftEnter`/`graphSearchEnter`，守卫判定统一走 `isImeComposing(e)`。
2. **新输入框优先非受控模式**：新增的文本输入（尤其预计跑在 Android WebView/壳内）优先
   `:value` + `@input`/`@compositionend`/`@change` 三事件同步 + 获焦期间 ~300ms DOM 轮询兜底
   （`@change` 在 Android 上比 input+compositionend 更可靠），关键路径禁依赖 v-model 单独兜底；
   轮询同步需判等（DOM 值与 model 相同则不写），失焦停表。
3. **存量输入框不回改**：现有登录/搜索/设置输入在浏览器实测正常，保持 v-model；
   仅当壳内真机暴露 IME 缺陷时，对问题输入框单独切换到第 2 条模式。
4. **壳红线**：壳内输入异常先确认容器配置——若用 Capacitor 必须 `android.captureInput: false`
   （true 会把 IME 提交转为末尾拼接，症状是光标中间插入落尾 + 无 input/composition 事件）；
   Tauri 用系统 WebView 无此陷阱。禁止恢复「光标意图追踪搬移」类方案（真机已验证失败）。
5. **验收纪律**：IME 修复/新输入框只能在**真机 + 真实输入法**下验收；模拟器与 CDP 合成事件
   仅作冒烟。验收清单：光标中间插入、连续中文、中英数字混排、退格、Enter 确认候选不误触发提交。
