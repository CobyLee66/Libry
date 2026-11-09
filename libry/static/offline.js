/* Libry 离线库 — IndexedDB 封装 + 增量下载队列 + 离线写队列（outbox）。
   同一份文件在页面与 Service Worker 两个上下文使用（sw.js 经 importScripts 加载），
   因此不得引用 window/document，统一走 globalThis；DOMParser 只在页面侧的
   syncContent 内使用（SW 不会调用）。无构建、无外部依赖。

   数据模型（DB: libry-offline）：
   - docs   keyPath ['user','file'] → {user, file, hash, payload, size, fetched_at}
     payload 为 /api/offline/doc 的完整 JSON（服务端渲染 HTML，客户端不复刻渲染管线）
   - meta   keyPath 'key' → current-user / manifest-<user> 等单值记录
   - outbox keyPath 'id' 自增 → {url, method, body, ts, user}（离线写操作，恢复在线按序回放） */
(function () {
  const DB_NAME = 'libry-offline';
  const DB_VERSION = 1;
  const ST_DOCS = 'docs';
  const ST_META = 'meta';
  const ST_OUTBOX = 'outbox';
  const DOWNLOAD_CONCURRENCY = 3;  // 对服务器友好；移动端弱网下也不至于打满
  const RATE_LIMIT_MAX_RETRIES = 5;   // 单个请求被限速后最多重试几轮
  const RATE_LIMIT_FALLBACK_SEC = 5;  // 服务端未给 Retry-After 时的指数退避起点
  const RATE_LIMIT_MAX_WAIT_SEC = 120; // 单次等待上限，防止异常响应让下载无限挂起

  let dbPromise = null;

  function openDb() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(ST_DOCS)) {
          db.createObjectStore(ST_DOCS, { keyPath: ['user', 'file'] });
        }
        if (!db.objectStoreNames.contains(ST_META)) {
          db.createObjectStore(ST_META, { keyPath: 'key' });
        }
        if (!db.objectStoreNames.contains(ST_OUTBOX)) {
          db.createObjectStore(ST_OUTBOX, { keyPath: 'id', autoIncrement: true });
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
    return dbPromise;
  }

  function reqAsPromise(req) {
    return new Promise((resolve, reject) => {
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  async function idbGet(store, key) {
    const db = await openDb();
    return reqAsPromise(db.transaction(store).objectStore(store).get(key));
  }

  async function idbPut(store, value) {
    const db = await openDb();
    return reqAsPromise(db.transaction(store, 'readwrite').objectStore(store).put(value));
  }

  async function idbDelete(store, key) {
    const db = await openDb();
    return reqAsPromise(db.transaction(store, 'readwrite').objectStore(store).delete(key));
  }

  async function idbGetAll(store, range) {
    const db = await openDb();
    return reqAsPromise(db.transaction(store).objectStore(store).getAll(range));
  }

  function userRange(user) {
    // file 路径不会包含 U+FFFF，bound 前闭后闭即覆盖该用户全部记录
    return IDBKeyRange.bound([user, ''], [user, '\uffff']);
  }

  /* Retry-After 解析：服务端按秒返回；兼容 HTTP date 形态；上限保护 */
  function parseRetryAfter(res) {
    const raw = res.headers.get('Retry-After');
    if (!raw) return 0;
    const seconds = Number(raw);
    if (Number.isFinite(seconds)) {
      return Math.max(0, Math.min(RATE_LIMIT_MAX_WAIT_SEC, seconds));
    }
    const at = Date.parse(raw);
    if (!Number.isNaN(at)) {
      return Math.max(0, Math.min(RATE_LIMIT_MAX_WAIT_SEC, (at - Date.now()) / 1000));
    }
    return 0;
  }

  function sleep(ms, signal) {
    return new Promise((resolve, reject) => {
      if (signal && signal.aborted) { reject(new Error('aborted')); return; }
      let timer = null;
      const onAbort = () => { clearTimeout(timer); reject(new Error('aborted')); };
      timer = setTimeout(() => {
        if (signal) signal.removeEventListener('abort', onAbort);
        resolve();
      }, ms);
      if (signal) signal.addEventListener('abort', onAbort, { once: true });
    });
  }

  /* 从渲染 HTML 中提取站内素材路径（raw/assets/ 下，SW 的素材策略会顺手写缓存） */
  function extractAssetPaths(html) {
    if (!html || typeof DOMParser === 'undefined') return [];
    try {
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const out = new Set();
      doc.querySelectorAll('img[src]').forEach((img) => {
        try {
          const u = new URL(img.getAttribute('src'), location.origin + '/');
          if (u.origin === location.origin && u.pathname.startsWith('/raw/assets/')) {
            out.add(u.pathname + u.search);
          }
        } catch (e) { /* 非法 src 忽略 */ }
      });
      return [...out];
    } catch (e) {
      return [];
    }
  }

  const API = {
    /* ---------------- 当前用户（页面登录后写入；SW 缓存/回放时读取） ---------------- */

    async setCurrentUser(user) {
      if (user) await idbPut(ST_META, { key: 'current-user', value: user });
      else await idbDelete(ST_META, 'current-user');
    },

    async currentUser() {
      const r = await idbGet(ST_META, 'current-user');
      return r ? r.value : '';
    },

    /* ---------------- 离线文档库 ---------------- */

    async saveDoc(user, file, hash, payload) {
      const size = JSON.stringify(payload).length;
      await idbPut(ST_DOCS, {
        user, file, hash: hash || '', payload, size,
        fetched_at: new Date().toISOString(),
      });
    },

    async getDoc(user, file) {
      const r = await idbGet(ST_DOCS, [user, file]);
      return r || null;
    },

    async deleteDoc(user, file) {
      await idbDelete(ST_DOCS, [user, file]);
    },

    async listDocs(user) {
      return idbGetAll(ST_DOCS, userRange(user));
    },

    async dropDocs(user) {
      const db = await openDb();
      const keys = await reqAsPromise(
        db.transaction(ST_DOCS).objectStore(ST_DOCS).getAllKeys(userRange(user)));
      if (!keys.length) return;
      const t = db.transaction(ST_DOCS, 'readwrite');
      const s = t.objectStore(ST_DOCS);
      keys.forEach((k) => s.delete(k));
      await new Promise((resolve, reject) => {
        t.oncomplete = resolve;
        t.onerror = () => reject(t.error);
        t.onabort = () => reject(t.error);
      });
    },

    async docStats(user) {
      const rows = await this.listDocs(user);
      return {
        count: rows.length,
        bytes: rows.reduce((a, r) => a + (r.size || 0), 0),
      };
    },

    /* ---------------- 清单快照（上次同步的服务器状态） ---------------- */

    async saveManifest(user, manifest) {
      const key = 'manifest-' + user;
      if (manifest) await idbPut(ST_META, { key, value: manifest });
      else await idbDelete(ST_META, key);
    },

    async getManifest(user) {
      const r = await idbGet(ST_META, 'manifest-' + user);
      return r ? r.value : null;
    },

    /* ---------------- 内容增量下载（页面上下文调用） ---------------- */

    async syncContent(user, opts = {}) {
      const onProgress = opts.onProgress || (() => {});
      const signal = opts.signal || null;
      const check = () => { if (signal && signal.aborted) throw new Error('aborted'); };
      check();

      let fatal = null;
      // 共享限速闸门：任一 worker 收到 429 后所有 worker 一起暂停，等 Retry-After
      // 过去再重试当前篇目，避免 3 个并发持续把滑动窗口打满、把合法请求记成失败。
      let gateUntil = 0;
      let done = 0;
      let total = 0;
      const emit = (ctx) => {
        const waiting = Math.max(0, Math.ceil((gateUntil - Date.now()) / 1000));
        onProgress({
          done,
          total,
          file: (ctx && ctx.file) || '',
          waiting: Math.min(waiting, RATE_LIMIT_MAX_WAIT_SEC),
        });
      };
      const waitGate = async (ctx) => {
        if (gateUntil <= Date.now()) return;
        while (gateUntil > Date.now()) {
          if (fatal) throw fatal;
          check();
          emit(ctx);
          await sleep(Math.min(1000, Math.max(1, gateUntil - Date.now())), signal);
        }
        emit(ctx);
      };
      const fetchRateLimited = async (url, ctx) => {
        let attempt = 0;
        for (;;) {
          await waitGate(ctx);
          if (fatal) throw fatal;
          check();
          const res = await fetch(url, { cache: 'no-store' });
          if (res.status !== 429) return res;
          attempt++;
          if (attempt > RATE_LIMIT_MAX_RETRIES) throw new Error('rate_limited');
          const wait = parseRetryAfter(res) || Math.min(
            RATE_LIMIT_MAX_WAIT_SEC,
            RATE_LIMIT_FALLBACK_SEC * Math.pow(2, attempt - 1));
          gateUntil = Math.max(gateUntil, Date.now() + wait * 1000);
        }
      };

      let res;
      try {
        res = await fetchRateLimited('/api/offline/manifest', { file: '' });
      } catch (e) {
        if (e.message === 'aborted' || e.message === 'rate_limited') throw e;
        throw new Error('network_failed');
      }
      if (res.status === 401) throw new Error('auth_required');
      if (!res.ok) throw new Error('manifest_failed');
      let manifest;
      try { manifest = await res.json(); } catch (e) { throw new Error('manifest_failed'); }
      const serverDocs = manifest.docs || {};

      const existing = await this.listDocs(user);
      const removed = existing.filter((r) => !serverDocs[r.file]).map((r) => r.file);
      for (const file of removed) await this.deleteDoc(user, file);

      const toFetch = [];
      for (const [file, info] of Object.entries(serverDocs)) {
        const local = existing.find((r) => r.file === file);
        // 本地无、hash 不同、或 hash 为空（访问即缓存的记录未验证过清单）都需要拉取
        if (!local || !local.hash || local.hash !== info.hash) {
          toFetch.push({ file, hash: info.hash });
        }
      }

      const failed = [];
      total = toFetch.length;
      emit({ file: '' });
      let cursor = 0;
      const worker = async () => {
        while (cursor < toFetch.length) {
          if (fatal) break;
          check();
          const job = toFetch[cursor++];
          const ctx = { file: job.file };
          try {
            const r = await fetchRateLimited(
              '/api/offline/doc?file=' + encodeURIComponent(job.file), ctx);
            if (r.status === 401) throw new Error('auth_required');
            if (!r.ok) throw new Error('doc_fetch_failed');
            const payload = await r.json();
            await this.saveDoc(user, job.file, job.hash, payload);
            for (const asset of extractAssetPaths(payload.html || '')) {
              check();
              await fetch(asset).catch(() => { /* 素材缺失离线时显示裂图，不阻塞 */ });
            }
          } catch (e) {
            if (signal && signal.aborted) { fatal = fatal || new Error('aborted'); break; }
            if (e.message === 'auth_required' || e.message === 'rate_limited') {
              fatal = fatal || e;
              break;
            }
            failed.push(job.file);  // 单篇失败不拖垮整库，结果里上报
          }
          done++;
          emit(ctx);
        }
      };
      await Promise.all(
        Array.from({ length: Math.min(DOWNLOAD_CONCURRENCY, toFetch.length) }, worker));
      if (fatal) throw fatal;

      await this.saveManifest(user, manifest);
      return {
        downloaded: done - failed.length,
        failed,
        removed: removed.length,
        total: Object.keys(serverDocs).length,
        generated_at: manifest.generated_at,
      };
    },

    /* ---------------- 离线写队列（outbox） ---------------- */

    async enqueueWrite(entry) {
      entry.user = entry.user || '';
      // 阅读进度是高频 LWW 写：同 URL 待回放条目直接替换为最新（语义与服务器 LWW 一致）
      if (entry.url === '/api/state/progress') {
        const all = await idbGetAll(ST_OUTBOX);
        const prev = all.find((e) => e.url === entry.url && e.user === entry.user);
        if (prev) {
          prev.body = entry.body;
          prev.ts = entry.ts;
          return idbPut(ST_OUTBOX, prev);
        }
      }
      return idbPut(ST_OUTBOX, entry);
    },

    async outboxCount(user) {
      const all = await idbGetAll(ST_OUTBOX);
      return all.filter((e) => !user || !e.user || e.user === user).length;
    },

    async clearOutbox(user) {
      const all = await idbGetAll(ST_OUTBOX);
      const doomed = all.filter((e) => !user || e.user === user);
      for (const e of doomed) await idbDelete(ST_OUTBOX, e.id);
    },

    /* 按入队顺序逐条回放当前用户的离线写；401 停下等重登录，429/5xx/断网留待下轮。
       fetchItem(item) 由调用方注入（app.js 负责给 LWW 端点注入 updated_at）。 */
    async replayOutbox(user, fetchItem) {
      const all = await idbGetAll(ST_OUTBOX);
      const mine = all.filter((e) => !user || e.user === user);
      let replayed = 0;
      const result = { replayed, remaining: mine.length, auth_expired: false, stalled: false };
      for (const item of mine) {
        try {
          const res = await fetchItem(item);
          if (res.status === 401) { result.auth_expired = true; break; }
          if (res.ok || res.status === 404) {  // 404 = 目标文档已不存在，回放无意义，出队
            await idbDelete(ST_OUTBOX, item.id);
            replayed++;
          } else {
            result.stalled = true;  // 429/5xx：保留队列，等下次在线事件重试
            break;
          }
        } catch (e) {
          result.stalled = true;  // 网络再次不可达
          break;
        }
      }
      result.replayed = replayed;
      result.remaining = await this.outboxCount(user);
      return result;
    },
  };

  globalThis.LibryOffline = API;
})();
