# 离线阅读与多端客户端架构

> 设计原则一句话：**离线能力做进 Web 层，原生壳只是薄壳**。在线时永远使用在线最新内容（网页更新不需要发版客户端），离线时由 Service Worker 回放缓存。

## 总体分层

```
┌─ Tauri 2 薄壳（clients/shell/，可选）─ 首启填服务器 URL → WebView 加载，零 IPC、零业务逻辑
│     └── 与浏览器 PWA 使用同一套 Web 层，桌面 PWA（Chrome「安装应用」）同样可用
├─ Web 离线层（libry/static/）
│   ├─ sw.js            # 在线优先的请求策略 + 壳预缓存 + 素材 SWR
│   └─ offline.js       # IndexedDB 离线库 + 增量下载队列 + 离线写队列（outbox），页面与 SW 共用
└─ 服务端数据通道（libry/server/）
    ├─ /raw/assets/            # vault 素材静态服务（会话校验，仅此子目录对外）
    ├─ GET /api/offline/manifest  # 可见文档 + 内容 sha256（增量协议）
    └─ GET /api/offline/doc?file= # 与 /api/doc 同构、无「已读」副作用
```

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
| 其余 `/api/` GET（meta/docs/session/bookmarks/marks…） | network-first → 缓存回退 | 离线启动时 `/api/session` 的缓存回放使应用无需强制登录即可进入 |
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

登出清理：当前用户 `docs` + manifest 删除、`current-user` 置空、通知 SW 清空 API
响应缓存（按 URL 缓存的列表/会话跨账户需失效）；outbox 保留（本人再登录后续传）。

## 增量下载协议

1. 客户端 `GET /api/offline/manifest` → `{generated_at, docs: {file: {title, type, updated, hash}}}`（hash 为源 md 的 sha256，服务端现场计算，不依赖索引新鲜度）。
2. 与本地 `docs` 按 `hash` 求差：新/变篇下载（`GET /api/offline/doc`），消失篇删除；hash 为空的本地记录（访问即缓存的）视为未验证、重新拉取。
3. 每篇下载后解析 HTML 中 `img[src]` 提取 `/raw/assets/` 引用逐个抓取（SW 的 SWR 策略顺手写缓存）。
4. 并发 3 节流；服务端离线端点独立限速（清单 30 次/分/IP、逐篇 600 次/分/IP），429 响应带 `Retry-After`，客户端按它暂停（进度条下方提示等待秒数）后自动续传，已下载内容保留；单篇 4xx/5xx/网络失败不阻塞整库，结果上报。

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

- 壳/PWA 离线**首次启动**必须至少在线一次（SW 注册后才能离线拉起）。
- 列表页离线依赖 SW 缓存的 `/api/docs` 精确 URL 命中，筛选变化后可能回退不全；
  离线管理页（`#/offline`）从离线库列已下载篇目，始终可靠。
- 关联图与全文搜索未进入离线 v1（graph 为可选 API；content.json 留作未来离线 FTS 备料）。

## 客户端形态

| 形态 | 获取方式 | 说明 |
|---|---|---|
| 浏览器 PWA | Chrome/Edge 打开站点 → 安装 | 桌面独立窗口 + Android 桌面图标；离线能力相同 |
| Tauri 薄壳 | `clients/` 构建（macOS/Windows/Android APK），或 CI artifacts | 首启填服务器地址；未签名包首次打开需手动放行 |
