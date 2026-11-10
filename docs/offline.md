# 离线阅读与多端客户端架构

> 设计原则一句话：**离线能力做进 Web 层，原生壳只是薄壳**。在线时永远使用在线最新内容（网页更新不需要发版客户端），离线时由 Service Worker 回放缓存。

## 总体分层

```
┌─ Tauri 2 薄壳（clients/shell/，可选）─ 首启填服务器 URL → WebView 加载，零 IPC
│     ├─ 连接页：探测可达即连；不可达进离线门户（不裸跳，杜绝系统错误页）
│     └─ 离线阅读器 reader.html + 镜像桥 bridge.html：壳 origin 的本地离线面（见下节）
├─ Web 离线层（libry/static/）
│   ├─ sw.js            # 在线优先的请求策略 + 壳预缓存 + 素材 SWR
│   └─ offline.js       # IndexedDB 离线库 + 增量下载队列 + 离线写队列（outbox），页面与 SW 共用
└─ 服务端数据通道（libry/server/）
    ├─ /raw/assets/            # vault 素材静态服务（会话校验，仅此子目录对外）
    ├─ GET /api/offline/manifest  # 可见文档 + 内容 sha256（增量协议）
    └─ GET /api/offline/doc?file= # 与 /api/doc 同构、无「已读」副作用
```

## 壳内离线阅读器与镜像（Android 的可靠离线面）

Android System WebView 对**远程站点**的 Service Worker 长期不可靠（注册/回放失败常见），
壳内离线浏览不能押在 SW 上。壳资产是本地文件、永远可加载，因此把离线数据面搬到壳 origin：

- **镜像桥**（`bridge.html`，壳资产）：远端 Web 应用「下载全部」后，经隐藏 iframe 加载
  壳资产桥页，postMessage 增量同步离线库到壳 origin 的 IndexedDB（同一 `libry-offline`
  结构，另含 `assets` store 存图片 dataURL）。桥回 ack 已存 hash 表，只发缺失/变化部分；
  对账删除服务器已移除的文档；登出/清除离线数据时同步清空壳库。
- **离线阅读器**（`reader.html`，壳资产）：纯 JS 渲染壳库——列表、正文（服务端渲染 HTML
  直接展示）、上下篇、图片（`/raw/assets` 替换为镜像 dataURL）。
- **离线门户**（连接页探测失败时的包装界面）：「进入离线阅读」直达壳内阅读器，
  任何网络失败都展示包装过的 UI，不再出现 WebView 系统错误页。
- 浏览器/桌面 PWA 无壳（`shellHome` 为空），自动跳过镜像，离线仍走 SW 路线（浏览器 SW 可靠）；
  桌面壳同时享有两条路线。服务器需在 CSP `frame-src` 放行 Tauri 壳 origin（见 `deploy/Caddyfile`）。
- 壳资产的 `lib/offline.js` 由各构建脚本与 CI 在构建时从 `libry/static/` 拷入（单一来源）。

## 为什么离线包缓存「渲染后 HTML」

正文渲染管线（wikilink 归一化、raw 降级、Python-Markdown、nh3 消毒）在服务端，
nh3 白名单是存储型 XSS 的唯一防线。客户端绝不复刻渲染管线——离线库缓存的
payload 就是 `GET /api/offline/doc` 的完整 JSON（html + meta + prev/next + 进度等），
离线阅读页与在线阅读页消费同一数据结构。

## 请求策略（sw.js）

| 请求类别 | 策略 | 说明 |
|---|---|---|
| 导航与壳资源（html/js/css/i18n/vendor/icon/manifest） | network-first（3.5s 超时）→ 缓存回退 | 在线=最新代码；SW 激活时解析首页引用做一次壳预缓存，保证「首次访问即断网」也能离线拉起 |
| `/api/doc?file=` | network-first → 成功时写入离线库（**访问即缓存层**）；失败回放离线库 | 访问过的文档自动具备离线能力 |
| `/api/offline/*` | 直通网络（不缓存、不回放，`cache: 'no-store'`） | 预取通道由 IndexedDB 管理；避免 3.5s 超时截断整库下载、超时后回放旧文档被按新 hash 保存，以及 API Cache 重复占用整库空间 |
| 其余 `/api/` GET（meta/docs/session/bookmarks/marks…） | network-first → 缓存回退 | 离线启动时 `/api/session` 的缓存回放使应用无需强制登录即可进入；缓存未命中（SW 合成 503）时页面侧按离线库 `current-user` 兜底进入离线模式 |
| `/raw/assets/` | stale-while-revalidate | 素材约定不可变；离线显示缓存副本 |
| 非 GET（写请求） | 不拦截 | 离线失败由应用层 outbox 排队（见下） |

缓存名不带版本号：条目随每次成功网络请求自然刷新，无版本迁移问题。fetch 统一
`cache: 'no-cache'` 绕开 HTTP 缓存的条件请求（no-cache + ETag 会回无 body 的 304，
无法进入 Cache API）。

## 离线数据模型（IndexedDB `libry-offline`，定义在 offline.js）

| store | key | 内容 |
|---|---|---|
| `docs` | `['user','file']` | `{hash, payload, size, fetched_at}`——**按账户隔离**（同设备多账户互不可见） |
| `meta` | `'key'` | `current-user`（页面登录后写、SW 读取）、`manifest-<user>`（上次同步的服务器清单快照） |
| `outbox` | 自增 `id` | `{url, method, body, ts, user}`——离线写操作，恢复在线按序回放 |
| `assets` | `['user','path']` | `{dataURL, saved_at}`——站内图片的 dataURL 副本（壳内离线阅读器断网渲染用，v2） |

登出清理：当前用户 `docs` + manifest 删除、`current-user` 置空、通知 SW 清空 API
响应缓存（按 URL 缓存的列表/会话跨账户需失效）；outbox 保留（本人再登录后续传）。

## 增量下载协议

1. 客户端 `GET /api/offline/manifest` → `{generated_at, docs: {file: {title, type, updated, hash}}}`（hash 为源 md 的 sha256，服务端现场计算，不依赖索引新鲜度）。
2. 与本地 `docs` 按 `hash` 求差：新/变篇下载（`GET /api/offline/doc`），消失篇删除；hash 为空的本地记录（访问即缓存的）视为未验证、重新拉取。
3. 每篇下载后解析 HTML 中 `img[src]` 提取 `/raw/assets/` 引用逐个抓取（SW 的 SWR 策略顺手写缓存）。
4. 并发 3 节流；逐篇端点不限速（整库下载是合法连发），清单端点限速 30 次/分/IP；单篇 4xx/5xx/网络失败不阻塞整库，结果上报。下载到的站内图片转 dataURL 存 `assets` store，随文档一并镜像到壳内离线阅读器（见上节）。
5. 离线管理页的「已下载文档」列表为可滚动表格：卡片加宽并减小侧边距，表头着色且吸顶，右侧常显自定义滚动条；每页最多 100 篇，按文章时间倒序（优先创建时间，最新在前），只保留标题与大小两列，长标题自动截断；IndexedDB 仍保留全量数据，分页不改变增量下载协议。

## 离线写队列（outbox）与冲突语义

覆盖写端点：已读/未读、阅读进度、手动书签、收藏及收藏标签、可见性、待删除标记。
离线失败时连同**动作发生时刻**入队；恢复在线（`online` 事件 / 启动在线 / 登录后）按
入队顺序逐条回放，**LWW 写端点回放时携带 `updated_at` = 原始动作时间**（服务端
`coerce_updated_at` 校验：非法/缺省回退服务器时间，未来值钳制）。

这样离线变更与在线多端变更共享同一套合并语义（`sync_data.py` CRDT）：
- `read` 单调并集；`progress`/`marks`/`bookmarks`/`visibility` per-file LWW——**动作发生晚者胜**；
- 回放遇 401 停下等重新登录；404（目标文档已删除）出队；429/5xx 留待下轮；
- 阅读进度是高频 LWW 写：outbox 内同 URL 条目合并为最新一条。

## 安全边界

- 离线端点与会话一致：`/api/offline/*` 校验会话、按 `can_see` 过滤；个人文档对无权者与不存在不可区分（404 同 `/api/doc`）。
- `/raw/assets` 是唯一暴露的 vault 内静态子目录（`raw/` 下文本原文仍不对外），要求有效会话，响应 `private, no-cache` 防共享代理留存认证内容；目录穿越由 StaticFiles 目录约束兜底。
- 离线库按账户隔离，登出即清；同一浏览器 profile 内多账户先后登录各自的缓存互不复用。

## 已知限制

- **客户端壳**的断网冷启动离线阅读走壳内镜像库，不依赖 SW（见「壳内离线阅读器与镜像」）；
  **浏览器/PWA** 仍依赖 SW：离线首次启动必须至少在线一次（SW 注册后才能离线拉起），且 SW
  仅在安全上下文（HTTPS 或 localhost）注册。SW 不可用时页面侧兜底保证应用打开期间可读，
  重启后无法拉起——离线管理页会给出提示。
- **页面侧离线兜底**（app.js）：`/api/session`、`/api/doc`、`/api/docs` 在 SW 缓存未命中
  （合成 503 `offline_not_cached`）或无 SW 网络直连失败时，应用直接回放 IndexedDB 离线库——
  会话按 `current-user` 进入离线模式、文档按已下载记录渲染（payload 与 `/api/doc` 同构）、
  列表按已下载记录的 meta 构造（支持 q/type/visibility/tags 筛选与排序，无已读状态/摘要）。
  离线读路径不依赖 SW 存活；SW 正常时仍由 sw.js 的缓存回放优先接管。
- 列表页：在线时依赖 SW 缓存的 `/api/docs` 精确 URL 命中，筛选变化后可能回退不全；
  离线时回退离线库列表（见上）。离线管理页（`#/offline`）始终直接读离线库，最可靠。
- 关联图与全文搜索未进入离线 v1（graph 为可选 API；content.json 留作未来离线 FTS 备料）。

## 客户端形态

| 形态 | 获取方式 | 说明 |
|---|---|---|
| 浏览器 PWA | Chrome/Edge 打开站点 → 安装 | 桌面独立窗口 + Android 桌面图标；离线能力相同 |
| Tauri 薄壳 | `clients/` 构建（macOS/Windows/Android APK），或 CI artifacts | 首启填服务器地址；未签名包首次打开需手动放行 |
