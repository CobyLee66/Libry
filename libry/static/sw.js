/* Libry 离线 Service Worker — 手写无构建，作用域为站点根（须挂在 /sw.js）。
   策略刻意「在线优先」，保证在线时永远是最新网页（网页更新无需客户端发版）：
   - 导航 / 壳资源 / API 读请求：network-first（3.5s 超时）→ 成功即刷新缓存条目 →
     失败（离线/超时）回退缓存；导航无精确命中时回退缓存的站点根
   - /api/doc?file=：成功时把响应写入 IndexedDB 离线库（访问即缓存层）；
     离线时从离线库按当前用户回放（多账户隔离）
   - /raw/assets/：stale-while-revalidate（素材约定不可变）
   - 非 GET 写请求不拦截：离线时由应用层 outbox（offline.js）排队回放
   缓存名不带版本号：条目随每次成功网络请求自然刷新，无需版本迁移。 */
importScripts('/offline.js');

const SHELL_CACHE = 'kb-shell';
const API_CACHE = 'kb-api';
const ASSET_CACHE = 'kb-assets';
const NET_TIMEOUT = 3500;
const CACHES = [SHELL_CACHE, API_CACHE, ASSET_CACHE];

self.addEventListener('install', () => self.skipWaiting());

/* 壳预缓存：解析站点首页引用的本地资源逐个拉取（html/js/css/i18n/vendor/icon/manifest）。
   首次访问即断网的场景必须能离线拉起整壳；条目随后由 network-first 自然刷新。
   预缓存失败（网络瞬断）不阻塞激活——下次访问的 network-first 会补齐。 */
async function precacheShell() {
  try {
    const cache = await caches.open(SHELL_CACHE);
    const root = await fetchNet('/', NET_TIMEOUT);
    if (!root.ok) return;
    await cache.put('/', root.clone());
    const html = await root.text();
    const refs = new Set();
    // src/href 的本地绝对路径值（含 ?v= 查询串，精确对应 network-first 的缓存键）
    for (const m of html.matchAll(/(?:src|href)="(\/[^"]+)"/g)) {
      refs.add(m[1]);
    }
    for (const ref of refs) {
      try {
        const u = new URL(ref, self.location.origin);
        if (u.origin !== self.location.origin) continue;
        const res = await fetchNet(u.href, NET_TIMEOUT);
        if (res.ok) await cache.put(u.href, res);
      } catch (e) { /* 单个资源失败不阻塞其余 */ }
    }
  } catch (e) { /* 网络不可达：跳过，待下次在线访问补齐 */ }
}

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    for (const name of await caches.keys()) {
      if (!CACHES.includes(name)) await caches.delete(name);
    }
    // 旧版本曾把离线预取响应缓存进 API Cache；现在改为直通，清掉升级前遗留副本
    const apiCache = await caches.open(API_CACHE);
    for (const req of await apiCache.keys()) {
      if (new URL(req.url).pathname.startsWith('/api/offline/')) {
        await apiCache.delete(req);
      }
    }
    await self.clients.claim();
    precacheShell();
  })());
});

self.addEventListener('message', (event) => {
  // 登出时由页面通知清空 API 响应缓存（列表/会话按 URL 缓存，跨账户需失效）
  if (event.data && event.data.type === 'clear-api-cache') {
    caches.delete(API_CACHE);
  }
  // 清除离线数据时由页面通知清空素材缓存——否则 storage.estimate 的占用数字不回落
  if (event.data && event.data.type === 'clear-asset-cache') {
    caches.delete(ASSET_CACHE);
  }
});

function fetchNet(req, timeoutMs) {
  // cache:'no-cache' 绕开 HTTP 缓存的条件请求（no-cache + ETag 会回 304 无 body 响应，
  // 无法放入 Cache API）；SW 缓存层自管新鲜度
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), timeoutMs);
  return fetch(req, { cache: 'no-cache', signal: ctl.signal })
    .finally(() => clearTimeout(timer));
}

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

async function networkFirst(req, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const res = await fetchNet(req, NET_TIMEOUT);
    if (res.ok) cache.put(req, res.clone());
    return res;
  } catch (e) {
    const hit = await cache.match(req);
    if (hit) return hit;
    if (req.mode === 'navigate') {
      const shell = await cache.match('/');
      if (shell) return shell;  // 离线深链进入时回退整壳
    }
    return jsonResponse({ detail: 'offline_not_cached' }, 503);
  }
}

async function staleWhileRevalidate(req, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(req);
  const refresh = fetchNet(req, NET_TIMEOUT)
    .then((res) => { if (res.ok) cache.put(req, res.clone()); return res; })
    .catch(() => null);
  return cached || (await refresh) || jsonResponse({ detail: 'offline_not_cached' }, 503);
}

async function docStrategy(req, url) {
  const file = url.searchParams.get('file') || '';
  try {
    const res = await fetchNet(req, NET_TIMEOUT);
    if (!res.ok) return res;  // 404/401 等业务语义直接透传，不做离线回放
    const user = await LibryOffline.currentUser();
    if (user && file) {
      try {
        // 访问即缓存：hash 留空，下次清单同步时按服务器 hash 校验补拉
        const payload = await res.clone().json();
        LibryOffline.saveDoc(user, file, '', payload).catch(() => {});
      } catch (e) { /* 响应体解析失败不影响主流程 */ }
    }
    return res;
  } catch (e) {
    const user = await LibryOffline.currentUser();
    if (user && file) {
      const rec = await LibryOffline.getDoc(user, file).catch(() => null);
      if (rec) return jsonResponse(rec.payload);
    }
    return jsonResponse({ detail: 'offline_not_cached' }, 503);
  }
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;  // 写请求不拦截：离线时应用层 outbox 排队
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  const path = url.pathname;

  if (path.startsWith('/raw/assets/')) {
    event.respondWith(staleWhileRevalidate(req, ASSET_CACHE));
    return;
  }
  if (path.startsWith('/api/offline/')) {
    // 离线预取通道由 IndexedDB 管理：直通网络，不缓存/不回放。
    // network-first 的 3.5s 超时与缓存回退会截断整库下载、回放旧文档（被按新 hash 保存），
    // 并在 API Cache 里重复占用一份整库空间。
    event.respondWith(fetch(req, { cache: 'no-store' }));
    return;
  }
  if (path === '/api/doc') {
    event.respondWith(docStrategy(req, url));
    return;
  }
  if (path.startsWith('/api/')) {
    event.respondWith(networkFirst(req, API_CACHE));
    return;
  }
  // 其余同源 GET：导航与壳资源（html/js/css/i18n/vendor/icon/manifest）
  event.respondWith(networkFirst(req, SHELL_CACHE));
});
