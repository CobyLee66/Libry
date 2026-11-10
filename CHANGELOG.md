# Changelog

All notable changes to this project are documented in this file.
本项目的所有重要变更都记录在此文件中。

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

Each entry is bilingual: English first, 中文随行。
每条变更均为中英双语：英文在前，中文在后。

## [Unreleased]

### Changed

- The client shell now handles an unreachable server gracefully instead of jumping into the WebView's system error page. On launch it shows a locked "Connecting…" screen while probing the saved server: reachable, it connects as before (latest web page); unreachable, it stays inside the shell and offers an offline portal — "Open offline reader" (a built-in shell reader backed by a mirror of your offline library), "Retry connection" and "Change server URL". The mirror syncs automatically after every "Download all / Check for updates" in the web app's offline manager (only missing or changed documents and images are sent) and is cleared on logout or when clearing offline data. The client shell version is bumped to 0.3.0.
  客户端壳现在会优雅处理服务器不可达，而不是跳进 WebView 系统错误页。启动时显示锁定的「连接中…」并探测上次服务器：可达照常连接（在线永远是最新网页）；不可达则停留在壳内，提供离线门户——「进入离线阅读」（壳内阅读器，数据来自离线库的壳内镜像）、「重试连接」与「更换服务器」。每次在 Web 应用离线管理页「下载全部/检查并更新」后自动镜像（只发送缺失或变化的文档与图片），登出或清除离线数据时同步清空。壳版本号升至 0.3.0。
- Per-document offline downloads are no longer rate-limited: the deliberate 600 hits/min/IP cap is gone, so large first-time downloads never stall or get truncated. The manifest endpoint keeps a 30 hits/min/IP guard against abuse (429 + Retry-After semantics remain only there).
  逐篇离线下载不再限速：删除了 600 次/分/IP 的刻意限制，首次整库下载不会再被截断。清单端点保留 30 次/分/IP 的防滥用限速（429 + Retry-After 语义仅对它保留）。

### Added

- Offline mode in the client shell now opens the **full web app** instead of a minimal reader. The shell bundles a snapshot of the whole web app; when offline, the offline portal's "Open offline reader" launches the exact same Vue application you use online, with a fetch shim answering `/api/*` from the shell's mirrored library — document list with search/filters/status tabs/sorting, article reading (TOC, previous/next, images), bookmarks page, marks page and settings all work offline. Reading progress is kept locally; other write actions report read-only (v1 boundary: cross-origin session writes are out of scope). The mirror also snapshots list/bookmarks/marks state at download time, and the portal shows how many documents are available offline.
  客户端壳的离线模式现在打开**完整 Web 应用**而非极简阅读器。壳内置整个 Web 应用的快照；断网时离线门户的「进入离线阅读」启动的就是与在线完全同款的 Vue 应用——fetch 垫片从壳内镜像库应答 `/api/*`：文档列表的搜索/筛选/状态页签/排序、正文阅读（目录、上下篇、图片）、收藏页、书签页与设置页全部离线可用。阅读进度本地生效；其余写操作提示只读（v1 边界：跨 origin 会话写入不在范围内）。镜像同时保存列表/收藏/书签状态快照，离线门户显示可离线阅读的文档数。
- The client shell now ships an offline reader and a mirror bridge: after downloading your library in the web app, documents and images are mirrored into the shell's own storage, so offline reading on Android works at cold start without relying on the WebView's Service Worker (unreliable for remote sites). The reader covers the document list, article bodies, previous/next navigation and images; the offline manager shows mirror progress. Deployments using the Caddy template need the updated `deploy/Caddyfile` (CSP `frame-src` now allows the Tauri shell origin).
  客户端壳新增离线阅读器与镜像桥：在 Web 应用下载离线库后，文档与图片会镜像进壳自己的存储，安卓端断网冷启动即可离线阅读，不再依赖 WebView 的 Service Worker（远程站点场景不可靠）。阅读器覆盖文档列表、正文、上下篇导航与图片；离线管理页显示镜像进度。使用 Caddy 模板的部署需同步更新 `deploy/Caddyfile`（CSP `frame-src` 放行 Tauri 壳 origin）。

- "Disconnect and change server" on the settings page (visible only inside the client shell): logs out and returns to the shell's server page. The remembered address is kept but no longer auto-connected on launch until you explicitly connect again; switching back to a previous server later keeps its offline downloads.
  设置页新增「断开连接并更换服务器」（仅客户端壳内显示）：注销当前会话并跳回壳的连接页。记住的服务器地址保留，但在再次主动连接之前启动时不再自动连接；之后切回原服务器时离线下载的缓存仍然保留。
- The offline manager now warns when the Service Worker is unavailable (plain-HTTP access, private browsing…): downloaded content stays readable in the running app, but the app cannot start offline after a restart.
  离线管理页在 Service Worker 不可用时（HTTP 明文访问、隐私浏览等）给出警告：运行中的应用仍可阅读已下载内容，但重启后无法离线进入。

### Fixed

- "Clear offline data" could silently do nothing: when an IndexedDB version upgrade was blocked by another page context (e.g. an outdated Service Worker holding the old database), every local-library operation hung without any error, so the confirm dialog closed and nothing changed. Database opens now time out with a visible error and yield to version upgrades, confirmation callbacks surface failures as a toast, and the offline manager additionally shows an always-accurate "document data" size next to the (lazily recycled) browser quota estimate.
  「清除离线数据」此前可能静默无效：当 IndexedDB 版本升级被其他页面上下文（如持有旧库的过期 Service Worker）阻塞时，所有本地库操作会无报错挂起——确认弹窗关闭后什么都没发生。现在数据库打开带超时与可见报错、并主动向版本升级让位；确认回调失败会以 toast 提示；离线管理页在浏览器配额统计（惰性回收）旁新增始终准确的「文档数据」体积。
- Confirmation dialogs are now app-rendered with localized buttons (确定/取消, OK/Cancel) — the native confirm() always showed browser-language OK/Cancel regardless of the app language. Applies to clearing offline data, clearing manual bookmarks, batch cleanup and user deletion.
  确认对话框改为应用内渲染、按钮可本地化（确定/取消、OK/Cancel）——原生 confirm() 的按钮文案始终跟随浏览器语言，与应用语言无关。覆盖清除离线数据、清除手动书签、批量清理与删除用户。
- Clearing offline data now also purges the Service Worker's cached vault images, and the offline manager shows an always-accurate "document data" size next to the browser quota estimate (the platform recycles the estimate lazily, so it kept showing stale numbers after clearing).
  清除离线数据现在会同时清空 Service Worker 缓存的 vault 图片；离线管理页在浏览器配额统计旁新增始终准确的「文档数据」体积（配额统计由系统惰性回收，清除后可能长时间显示旧值）。
- Offline mode no longer breaks at the first network failure. Entering the app offline works even when the Service Worker's cached session is missing — the session check now treats the SW's synthesized "offline, not cached" response as offline and enters with the locally remembered account instead of bouncing to a login screen that cannot log in. Documents downloaded to the offline library open offline even if the Service Worker is missing or its cache misses (the page replays them directly from IndexedDB), and the document list falls back to the locally downloaded library (title/type/tag filtering) instead of going blank. Also fixed an uncaught error when marking a document unread offline.
  离线模式不再因第一次网络失败而失效。SW 缓存的会话缺失时也能离线进入应用——会话检查现在把 SW 合成的「离线且未缓存」响应视为离线，用本地记住的账户直接进入，而不是弹到无法登录的登录页；已下载到离线库的文档在 SW 缺失或缓存未命中时也能离线打开（页面直接回放 IndexedDB）；文档列表回退为本地已下载库（支持标题/类型/标签筛选）而非空白。另修复离线标记未读时的未捕获异常。

- "Disconnect and change server" on the settings page (visible only inside the client shell): logs out and returns to the shell's server page. The remembered address is kept but no longer auto-connected on launch until you explicitly connect again; switching back to a previous server later keeps its offline downloads.
  设置页新增「断开连接并更换服务器」（仅客户端壳内显示）：注销当前会话并跳回壳的连接页。记住的服务器地址保留，但在再次主动连接之前启动时不再自动连接；之后切回原服务器时离线下载的缓存仍然保留。

### Fixed

- Offline manager: the downloaded-document list is now a scrollable two-column table (title, size), paginated at 100 per page and sorted by article time (newest first). Dates and status labels are no longer shown, giving most of the width to titles; the list card uses the full content width with reduced side padding, a tinted sticky header and an always-visible custom scrollbar, and a large library no longer renders every downloaded document at once.
  离线管理页：「已下载文档」列表改为可滚动两列表格（标题、大小），每页最多 100 篇，按文章时间倒序（最新在前）；日期与状态标签不再显示，把大部分宽度留给标题。列表卡片加宽并减小侧边距，表头着色且吸顶，右侧常显自定义滚动条；大书库也不再一次性渲染全部已下载文档。

### Changed

- Slimmer top bars: the filter button moved from the list header to the left edge of the status-tab row (pinned there while the tabs scroll horizontally on narrow screens), and the logout and offline-download buttons are gone from every page header. Logout and the offline manager now live as cards on the settings page, freeing width for the search bar on phones.
  顶栏瘦身：过滤按钮从列表页顶栏移到状态 tab 行最左（窄屏 tab 横向滚动时保持钉住）；所有页面顶栏不再放置退出登录与离线下载按钮。退出登录与离线管理改为设置页中的卡片入口，为手机端搜索框让出宽度。

### Fixed

- Client connection page: the "Server unreachable" hint was written to a hidden element and therefore never actually shown; it now appears on the connection card when the reachability probe fails.
  客户端连接页：「服务器不可达」提示此前写在隐藏元素上、从未真正显示；现在探测失败时会正常显示在连接卡片上。
- Secondary buttons inside cards (e.g. "Check for updates" on the offline page and "Sync now" in settings) no longer lose their label after a tap on Android. The card button rule paints a blue background while `.btn:hover` turned the text blue too; Android's sticky hover kept that state after the tap (and while the button was disabled). Card buttons now keep white text on hover. The rule is documented in `docs/frontend-style.md`.
  卡片内的次级按钮（离线页「检查并更新」、设置页「立即同步」等）在 Android 上点击后不再出现无文字状态：卡片按钮规则给蓝底，而 `.btn:hover` 又把文字改成蓝色，触屏的粘滞 hover 让该状态一直保持（按钮处于 disabled 时也一样）。现卡片内 `.btn:hover` 保持白字；规则已写入 `docs/frontend-style.md`。

## [0.4.0] - 2026-11-09

### Added

- Offline reading: the web app now works without a network. A hand-written Service Worker keeps an online-first policy (visits always get the latest web code, so web updates never require a client release), caches visited documents and vault images, and an "Offline reading" manager page (`#/offline`) handles bulk download with incremental updates (server-side content hashes), storage usage and per-account clearing. Offline writes (read/unread, progress, position bookmarks, favorites and tags, visibility, deletion marks) queue in an outbox and replay automatically — with their original action timestamps — once back online, merging with other devices under the same LWW semantics. The site can also be installed as a PWA (manifest + icons). See `docs/offline.md`.
  离线阅读：Web 端支持无网络使用。手写 Service Worker 坚持「在线优先」（在线访问永远拿最新网页代码，网页更新无需发版客户端），自动缓存访问过的文档与 vault 图片；新增「离线阅读」管理页（`#/offline`），支持按内容哈希增量下载全库、查看存储占用、按账户清除。离线期间的写操作（已读/未读、阅读进度、位置书签、收藏及标签、可见性、删除标记）进入 outbox 队列，恢复网络后**携带原始动作时间**自动回放，与在线多端共享同一套 LWW 合并语义。站点可安装为 PWA（manifest + 图标）。详见 `docs/offline.md`。
- Optional `updated_at` on write endpoints (`POST /api/state/progress`, `POST/DELETE /api/marks`, `POST/PUT/DELETE /api/bookmarks`, `POST /api/visibility`): offline clients replay queued writes with the original action time so cross-device LWW compares action time, not replay time. Server-side fallback to server time keeps old clients unchanged (no breaking change).
  写端点新增可选 `updated_at`（`POST /api/state/progress`、`POST/DELETE /api/marks`、`POST/PUT/DELETE /api/bookmarks`、`POST /api/visibility`）：离线客户端回放队列时携带原始动作时间，跨端 LWW 按动作时间而非回放时间比较；缺省回退服务器时间，旧客户端行为不变（无破坏性变更）。
- Vault asset serving: `GET /raw/assets/{path}` now serves vault images (session required, `private, no-cache`; `raw/` text sources remain unexposed). Documents referencing `raw/assets` images (per the vault template convention) display correctly for the first time.
  vault 素材服务：新增 `GET /raw/assets/{path}`（需会话，`private, no-cache`；`raw/` 下文本原文仍不对外暴露）。按 vault 模板约定引用 `raw/assets` 图片的文档首次得以正常显示。
- Multi-platform thin clients under `clients/` (macOS / Windows / Android via Tauri 2): a zero-IPC WebView shell with a first-run page for entering your own Libry server URL; offline capability lives entirely in the web layer, so web updates never require a client release. Build instructions in `clients/README.md`, CI artifacts via `.github/workflows/clients.yml`.
  `clients/` 下新增多端薄壳客户端（Tauri 2，覆盖 macOS / Windows / Android）：零 IPC 的 WebView 容器 + 首启「填写自家服务器地址」页；离线能力全部在 Web 层，网页更新无需发版客户端。构建说明见 `clients/README.md`，CI 产物见 `.github/workflows/clients.yml`。

### Changed

- Android safe-area handling: the shell's `MainActivity` (template defaults to edge-to-edge) now applies system-bar/cutout/keyboard insets as padding around the WebView, so the status bar, display cutout and gesture bar no longer cover the web content; the revealed strips use the site background color. The patch lives in `clients/android-custom/` and is re-applied by `build-android.sh` and CI on every build.
  Android 安全区适配：壳的 `MainActivity`（模板默认 edge-to-edge，内容画进系统栏下面）现按「系统栏 + 刘海 + 键盘」insets 给 WebView 打 padding，状态栏/刘海/手势条不再遮挡网页内容，让出的区域填站点底色。补丁位于 `clients/android-custom/`，由 `build-android.sh` 与 CI 每次构建自动应用。
- Client icons now come from a single source (`libry/static/icon.png`): `clients/scripts/build-icons.sh` regenerates the shell start-page logo, PWA manifest icons and the full Tauri icon set (icns/ico/Android mipmap/iOS AppIcon) from it; the Android build re-syncs launcher icons into the generated project on every build, so icon changes propagate without re-init. The adaptive-icon foreground is re-rendered with the artwork at 2/3 of the canvas (the launcher-visible area), fixing the heavily cropped edges the stock Tauri full-canvas foreground produced; the PWA manifest no longer declares `maskable` for the same reason.
  客户端图标改为单一来源（`libry/static/icon.png`）：`clients/scripts/build-icons.sh` 从它再生成壳首启页 logo、PWA manifest 图标与 Tauri 全平台图标集（icns/ico/Android mipmap/iOS AppIcon）；Android 构建每次把启动图标同步进生成的工程，图标变更无需重新 init 即可生效。自适应图标前景层按画布 2/3（即启动器可见区）重排——修复 Tauri 默认满画布前景导致的边缘大面积裁剪；PWA manifest 出于同样原因不再声明 `maskable`。
- `clients/` gains platform build/install scripts modeled after the Coby-AI-Learning project's `scripts/` conventions (OS auto-detection, env-var overrides, pre-flight checks, artifacts under `clients/dist/`): `build-macos.sh`, `build-windows.sh`, `build-android.sh` (build + zipalign + signing + optional auto-install), `install-apk.sh`, `build-icons.sh`. See `clients/scripts/readme.md`.
  `clients/` 新增各平台构建/安装脚本，约定参照 Coby-AI-Learning 项目的 `scripts/`（操作系统自适应、环境变量覆盖、pre-flight 检查、产物统一 `clients/dist/`）：`build-macos.sh`、`build-windows.sh`、`build-android.sh`（构建 + zipalign + 签名 + 可选自动安装）、`install-apk.sh`、`build-icons.sh`。详见 `clients/scripts/readme.md`。

- Vault template convention: source pages now embed the full original text under `## 原文全文（<version/date>）` instead of prefixing "附录" (Appendix); parallel sections are named after their content (e.g. `## ASR 逐字稿`, `## 评论区`) rather than "附录 A/B". Applies to the generated vault `AGENTS.md`, the bundled `kb-ingest` skill, the `make_appendix.py` helper description and the test fixture; existing vaults are unaffected (old headings stay valid).
  模板规范调整：source 页原文全文的锚点由 `## 附录：原文全文（<版本/日期>）` 改为 `## 原文全文（<版本/日期>）`，不再加「附录」前缀；并列段落直呼内容名（如 `## ASR 逐字稿`、`## 评论区`），不用「附录 A/B」。涉及 `libry init` 生成的 vault `AGENTS.md`、内置 `kb-ingest` skill、`make_appendix.py` 说明与测试夹具；存量 vault 不受影响，旧标题仍视为合法锚点。

### Fixed

- Mobile reader: stabilized the auto-hiding action row on Android by requiring accumulated scroll movement before toggling and adding a top buffer, so small rebound events right after it hides no longer make it flicker open.
  手机端阅读页：工具栏显隐改为按累计滚动位移判断，并在顶部增加缓冲区，修复 Android 上工具栏刚收起时被细碎回弹事件反复展开、快速抖动的问题。
- Markdown images referencing in-vault assets (`![alt](../raw/assets/….png)`) were stripped down to plain text by the raw-link downgrade pass, so documents never showed their images; the link regex now skips image syntax and images render through the new asset route.
  引用站内素材的 markdown 图片（`![alt](../raw/assets/….png)`）曾被 raw 链接降级逻辑误剥成纯文本，导致文档图片始终无法显示；链接正则现排除图片语法，图片经新素材路由正常渲染。
- Chinese IME hardening: Enter-key handlers on the bookmark-tag editor and the graph search box now ignore key events during IME composition (`isComposing`/`keyCode 229`), so confirming a candidate no longer submits prematurely; the rules are documented in `docs/frontend-style.md` for all future text inputs.
  中文输入法加固：收藏标签编辑框与图谱搜索框的回车处理现忽略组词期间的按键（`isComposing`/`keyCode 229`），确认候选不再误触发提交；规则已写入 `docs/frontend-style.md`，约束后续所有文本输入实现。

## [0.3.0] - 2026-10-05

### Added

- Reading progress memory: scrolling in the reader auto-reports the position (debounced), reopening an article restores the scroll position with a toast, and a "Continue reading" card on the list page jumps back to the most recent unfinished article. Entries are removed automatically once you reach 98%, so the progress list only holds articles you are actually mid-way through. Stored per account in `state.json` (`progress`) and merged across nodes with per-file LWW.
  阅读进度记忆：阅读页滚动自动防抖上报位置，再次打开文章自动恢复滚动位置并提示；列表页顶部「继续阅读」卡片可跳回最近未读完的文章。读到 98% 自动清除条目，进度列表只保留真正读了一半的文章。按账户存于 `state.json`（`progress`），跨端按 file 级 LWW 合并。
- Bookmarks (reading-position marks): a ribbon button in the reader saves a bookmark at the current scroll position (one per article, tapping again moves it); a new `#/marks` bookmarks page lists "Reading progress" and "My bookmarks" with progress bars, jump-back and delete; a ribbon entry in the list-page toolbar opens it. Stored per account in `state.json` (`marks`) with tombstones, merged across nodes with per-file LWW. New endpoints: `GET/POST/DELETE /api/marks`, `POST/DELETE /api/state/progress`; `GET /api/doc` now returns `progress`/`marked`, `GET /api/meta` returns `continue_reading` — see `docs/api.md`.
  书签（阅读位置标记）：阅读页缎带按钮在当前滚动位置添加书签（每篇一个，再次点击即移动位置）；新增 `#/marks` 书签页，分「阅读进度」「我的书签」两节，带进度条、可跳回可删除；列表页工具栏新增缎带入口。按账户存于 `state.json`（`marks`，含墓碑），跨端按 file 级 LWW 合并。新端点：`GET/POST/DELETE /api/marks`、`POST/DELETE /api/state/progress`；`GET /api/doc` 新增 `progress`/`marked` 字段，`GET /api/meta` 新增 `continue_reading` 字段——详见 `docs/api.md`。
- Bilingual README: `README.md` (English, primary) + `README.zh-CN.md` (中文), cross-linked at the top, with product screenshots (`docs/images/`) captured from a demo vault generated by `libry init`.
  双语 README：`README.md`（英文主）+ `README.zh-CN.md`（中文副），顶部互链，产品截图（`docs/images/`）均拍自 `libry init` 生成的演示 vault。
- Documentation maintenance contract in `AGENTS.md`: README dual-file sync rule and CHANGELOG rules (Keep a Changelog + SemVer, bilingual entries, `[Unreleased]` staging, bottom compare links).
  `AGENTS.md` 新增文档维护契约：README 双文件同步规则与 CHANGELOG 维护规则（Keep a Changelog + SemVer、双语条目、`[Unreleased]` 暂存、底部 compare 链接）。
- Sensitive-data discipline section in `AGENTS.md` (public-repo rules: placeholder conventions, screenshot discipline, pre-commit self-check); `.gitignore` now covers `.env`, `*.pem`, `*.key` and local env scripts.
  `AGENTS.md` 新增「敏感信息纪律」小节（公开仓库规则：占位符约定、截图纪律、提交前自查）；`.gitignore` 补 `.env`、`*.pem`、`*.key` 与本地环境脚本。

### Changed

- Favorites icon changed from the bookmark ribbon to a star (the ribbon now means "bookmarks" = reading positions); English UI labels renamed Bookmarks → Favorites. Internal names (`bookmarks.json`, `/api/bookmarks`, i18n key namespace `bm.*`) are unchanged. `state.json` gains `progress`/`marks` keys — old files load fine, but upgrade all nodes together: pre-upgrade nodes drop the new keys when their older merge logic writes `state.json`.
  收藏图标由书签缎带改为星形（缎带图标让给「书签=阅读位置」）；英文界面文案 Bookmarks → Favorites。内部命名（`bookmarks.json`、`/api/bookmarks`、i18n 键 `bm.*`）不变。`state.json` 新增 `progress`/`marks` 键——旧文件读取自动兼容，但混版本集群中旧节点的合并逻辑会在写盘时丢弃新键，请所有节点一起升级。
- Mobile reading-page header: title and action buttons now split into two rows (row 1: back + title, always visible; row 2: quick-action buttons). The button row auto-hides when scrolling down and reappears when scrolling up, so it no longer squeezes the title or wastes reading space.
  手机端阅读页顶栏优化：标题与操作按钮分两行显示（第一行返回+标题常驻，第二行快捷操作按钮），向下滚动时按钮行自动隐藏、向上滚动时恢复，标题不再被挤压，也不占用正文阅读空间。
- `CHANGELOG.md` migrated to the Keep a Changelog 1.1.0 format with bilingual entries and version compare links.
  `CHANGELOG.md` 迁移为 Keep a Changelog 1.1.0 格式，条目双语化并补版本 compare 链接。

### Fixed

- Read marks pending in the 30-second debounce window are no longer lost when the server stops via SIGTERM (the normal systemd/launchd stop path): uvicorn exits on SIGTERM without running `atexit` handlers, so the pending-state flush now also runs from a FastAPI shutdown (lifespan) hook. This affects the new reading progress as well.
  修复服务经 SIGTERM 停止（systemd/launchd 的常规停止方式）时丢失 30 秒防抖窗口内已读标记的问题：uvicorn 收到 SIGTERM 退出时不执行 `atexit`，未落盘改动的刷盘改由 FastAPI shutdown（lifespan）钩子同时承担；新加的阅读进度同样受益。
- Mobile reader: fixed the header button row rapidly flickering between collapsed and expanded when scrolling down near the bottom of an article. Collapsing used to shrink the sticky header's in-flow height, which shrank the whole page; the browser then clamped `scrollY`, and that clamping event looked like an "up-scroll", re-expanding the row — a loop whose visibility depended on frame timing (hence intermittent). The button row is now an overlay hanging below the header edge and no longer affects page height; the top padding of `.doc-body` makes room for it when expanded.
  修复手机端阅读页滚动到文章底部附近时顶栏按钮行在收起/展开间快速反复抖动的问题：原实现收起时会压缩 sticky 顶栏在文档流中的高度、使页面总高缩小，浏览器随之钳制 `scrollY`，钳制产生的反向滚动事件被误判为上滑又重新展开，形成循环（是否发作取决于帧时序，故表现为偶发）。按钮行改为挂在顶栏下沿的浮层，不再影响页面高度；`.doc-body` 顶部留白为展开态浮层让位。

## [0.2.0] - 2026-09-21

### Added

- Bilingual (Chinese/English) web UI via `libry/static/i18n/` — a hand-rolled lightweight runtime with no new dependencies and no build step. Language auto-detects from the browser (`zh*` → 中文, everything else falls back to English) and can be switched manually via the language dropdown on the login card and settings page (persisted to `localStorage['kb-lang']`).
  Web 端支持中英双语：`libry/static/i18n/`（手写轻量运行时，无新增依赖、无构建）。默认按浏览器语言自动检测（`zh*` → 中文，其余回退 English）；登录卡与设置页的语言下拉可手动切换（不占顶栏空间），持久化到 `localStorage['kb-lang']`。
- A foundation for future languages: adding one = one dictionary file + one `<script>` line in `index.html` + one mapping in `i18n/core.js` `detect()`; `t()` supports `{name}` interpolation and `{one, other}` plurals via `Intl.PluralRules`.
  为后续语言打好基础：新增语言 = 加一个字典文件 + `index.html` 一行 `<script>` + `i18n/core.js` 的 `detect()` 一处映射；`t()` 支持 `{name}` 插值与 `{one, other}` 复数（`Intl.PluralRules`）。
- `tests/test_i18n.py`: dictionary key-set consistency across languages, missing-key detection for template/JS references, and dictionary file mounting checks.
  新增 `tests/test_i18n.py`：各语言 key 集合一致性、模板/JS 引用漏键、字典文件挂载检查。

### Changed

- **BREAKING**: `HTTPException` `detail` values changed from Chinese prose to stable snake_case error codes (e.g. `invalid_credentials`) — the full list is in `docs/api.md`. Script consumers must branch on error codes, never parse natural-language text.
  **BREAKING**：`HTTPException` 的 `detail` 由中文文案改为稳定错误码（snake_case，如 `invalid_credentials`），完整清单见 `docs/api.md`；脚本消费者请按错误码判断，不要解析自然语言文案。
- **BREAKING**: `GET /api/deletions/status` (`.libry/purge-status.json`) — `ok` results now carry structured `pages` (deleted page count) / `refs` (cleaned reference count) fields instead of natural-language `detail`; on `error`, `detail` now holds the raw diagnostic output (e.g. `publish.sh: <stderr>`), passed through verbatim by the frontend.
  **BREAKING**：`GET /api/deletions/status`（`.libry/purge-status.json`）：`ok` 结果新增结构化 `pages`（删除页数）/`refs`（清理引用数）字段，不再写自然语言 `detail`；`error` 的 `detail` 改存原始诊断输出（如 `publish.sh: <stderr>`），由前端原样透出。

## [0.1.0] - 2026-09-20

First public release.
首个公开版本。

### Added

#### Engine / 引擎

- `libry init`: vault scaffolding (AGENTS.md contract + agent skills + sample content + random secrets + admin password + git).
  `libry init`：vault 脚手架（AGENTS.md 契约 + agent skills + 示例内容 + 随机密钥 + admin 密码 + git）。
- `libry serve`: FastAPI + Vue 3 web app (multiple accounts, read/new tracking, bookmarks, personal/shared visibility, deletion marking).
  `libry serve`：FastAPI + Vue 3 web 端（多账户、已读/新增、收藏夹、个人/共享可见性、删除标记）。
- `libry index` / `graph` / `purge` / `sync-data` / `passwd` / `config` / `skills` / `lint` CLI commands.
  `libry index` / `graph` / `purge` / `sync-data` / `passwd` / `config` / `skills` / `lint` CLI。
- Single source of configuration: `libry.toml` at the vault root + environment variables (`KB_ROOT` / `KB_DATA_DIR` / `KB_ROLE` / `KB_GIT_BRANCH` / `KB_LOCAL_URL` / `KB_DEPLOY_KEY`).
  配置单一来源：vault 根 `libry.toml` + 环境变量（`KB_ROOT` / `KB_DATA_DIR` / `KB_ROLE` / `KB_GIT_BRANCH` / `KB_LOCAL_URL` / `KB_DEPLOY_KEY`）。
- The relation graph is an optional component (`pip install 'libry[graph]'`, local embeddings via fastembed, graceful degradation when absent).
  关联图为可选组件（`pip install 'libry[graph]'`，fastembed 本地 embedding，缺失时优雅降级）。
- Cross-node user-data sync: CRDT-style LWW + deletion tombstones, merged bidirectionally through the vault's git repo.
  用户数据跨端同步：CRDT 风格 LWW + 删除墓碑，经 vault git 仓库双向合并。

#### Agent workflow / Agent 工作流

- The vault template ships 5 skills: kb-ingest / kb-lint / kb-publish / kb-query / kb-research-ingest (example).
  vault 模板自带 5 个 skills：kb-ingest / kb-lint / kb-publish / kb-query / kb-research-ingest（示例）。
- `tools/lint/`: 7 structural check scripts (wikilinks / orphans / index / frontmatter / dead links / sources / rendering), all driven by `libry lint`.
  `tools/lint/`：7 个结构检查脚本（wikilink/孤儿/索引/frontmatter/死链/sources/渲染），`libry lint` 一键跑。
- `scripts/run-ingest.sh` / `run-lint.sh`: headless execution of any coding agent via the `KB_AGENT_CMD` abstraction; `notify.sh` for generic webhook notifications.
  `scripts/run-ingest.sh` / `run-lint.sh`：`KB_AGENT_CMD` 抽象驱动任意 coding agent 无头执行；`notify.sh` 通用 webhook 通知。

#### Deployment / 部署

- `deploy/install.sh`: bare-metal install (venv + systemd / launchd self-service setup).
  `deploy/install.sh`：裸机安装（venv + systemd / launchd 自助安装）。
- `deploy/publish.sh` / `sync.sh` / `update.sh` / `sync-data.sh`: multi-node sync pipeline (webhook + cron dual channel).
  `deploy/publish.sh` / `sync.sh` / `update.sh` / `sync-data.sh`：多机同步链路（webhook + cron 双通道）。
- Neutral systemd / launchd / crontab / Caddy templates.
  systemd / launchd / crontab / Caddy 中性模板。

[Unreleased]: https://github.com/CobyLee66/Libry/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/CobyLee66/Libry/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/CobyLee66/Libry/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/CobyLee66/Libry/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/CobyLee66/Libry/releases/tag/v0.1.0
