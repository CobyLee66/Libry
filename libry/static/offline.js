/* Libry 离线库 — IndexedDB 封装 + 增量下载队列 + 离线写队列（outbox）。
   同一份文件在页面与 Service Worker 两个上下文使用（sw.js 经 importScripts 加载），
   因此不得引用 window/document，统一走 globalThis；DOMParser 只在页面侧的
   syncContent 内使用（SW 不会调用）。无构建、无外部依赖。

   数据模型（DB: libry-offline）：
   - docs   keyPath ['user','file'] → {user, file, hash, payload, size, fetched_at}
     payload 为 /api/offline/doc 的完整 JSON（服务端渲染 HTML，客户端不复刻渲染管线）
   - meta   keyPath 'key' → current-user / manifest-<user> 等单值记录
   - outbox keyPath 'id' 自增 → {url, method, body, ts, user}（离线写操作，恢复在线按序回放）
   - assets keyPath ['user','path'] → {user, path, dataURL, saved_at}
     站内图片素材的 dataURL 副本：供壳内离线阅读器断网渲染（v2 新增） */
(function () {
  const DB_NAME = 'libry-offline';
  const DB_VERSION = 2;
  const ST_DOCS = 'docs';
  const ST_META = 'meta';
  const ST_OUTBOX = 'outbox';
  const ST_ASSETS = 'assets';
  const DOWNLOAD_CONCURRENCY = 3;  // 对服务器友好；移动端弱网下也不至于打满

  let dbPromise = null;

  function openDb() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise((resolve, reject) => {
      let settled = false;
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
        if (!db.objectStoreNames.contains(ST_ASSETS)) {
          db.createObjectStore(ST_ASSETS, { keyPath: ['user', 'path'] });
        }
      };
      req.onsuccess = () => {
        if (settled) { try { req.result.close(); } catch (e) { /* 已让位 */ } return; }
        settled = true;
        const db = req.result;
        // 旧版本上下文（如更新前的 Service Worker 代码）请求升级版本时主动让位，
        // 否则它持有的旧连接会把这里的新版本打开请求无限阻塞
        db.onversionchange = () => {
          try { db.close(); } catch (e) { /* 已关闭 */ }
          if (dbPromise === p) dbPromise = null;
        };
        resolve(db);
      };
      req.onerror = () => {
        if (settled) return;
        settled = true;
        dbPromise = null;
        reject(req.error);
      };
      // 阻塞可见化：旧连接不肯让位时不能让所有本地库操作静默挂起——
      // 超时报错并复位缓存，占用释放后下一次调用重试即自愈
      setTimeout(() => {
        if (settled) return;
        settled = true;
        dbPromise = null;
        try { if (req.result) req.result.close(); } catch (e) { /* 未就绪 */ }
        reject(new Error('idb_blocked'));
      }, 10000);
    });
    const p = dbPromise;
    return p;
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

  /* Blob → dataURL：素材镜像到壳内离线阅读器时经 postMessage 传输用 */
  function blobToDataURL(blob) {
    return new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onload = () => resolve(r.result);
      r.onerror = () => reject(r.error);
      r.readAsDataURL(blob);
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

    /* ---------------- 素材镜像（壳内离线阅读器断网渲染图片用） ---------------- */

    async saveAsset(user, path, dataURL) {
      await idbPut(ST_ASSETS, { user, path, dataURL, saved_at: new Date().toISOString() });
    },

    async getAsset(user, path) {
      const r = await idbGet(ST_ASSETS, [user, path]);
      return r ? r.dataURL : null;
    },

    async dropAssets(user) {
      const db = await openDb();
      const keys = await reqAsPromise(
        db.transaction(ST_ASSETS).objectStore(ST_ASSETS).getAllKeys(userRange(user)));
      if (!keys.length) return;
      const t = db.transaction(ST_ASSETS, 'readwrite');
      const s = t.objectStore(ST_ASSETS);
      keys.forEach((k) => s.delete(k));
      await new Promise((resolve, reject) => {
        t.oncomplete = resolve;
        t.onerror = () => reject(t.error);
        t.onabort = () => reject(t.error);
      });
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

    /* ---------------- 本地模式状态快照（完整 UI 垫片的数据源） ---------------- */

    async saveSnapshot(user, snapshot) {
      const key = 'snapshot-' + user;
      if (snapshot) await idbPut(ST_META, { key, value: snapshot });
      else await idbDelete(ST_META, key);
    },

    async getSnapshot(user) {
      const r = await idbGet(ST_META, 'snapshot-' + user);
      return r ? r.value : null;
    },

    /* ---------------- 内容增量下载（页面上下文调用） ---------------- */

    async syncContent(user, opts = {}) {
      const onProgress = opts.onProgress || (() => {});
      // onAsset(path, dataURL)：抓到的站内素材交给调用方（镜像到壳内离线阅读器用）；
      // 未提供时仅预热 HTTP 缓存（在线 SW 的素材策略会顺手写缓存）
      const onAsset = opts.onAsset || null;
      const signal = opts.signal || null;
      const check = () => { if (signal && signal.aborted) throw new Error('aborted'); };
      check();

      let fatal = null;
      let done = 0;
      let total = 0;
      const emit = (ctx) => {
        onProgress({ done, total, file: (ctx && ctx.file) || '' });
      };

      let res;
      try {
        res = await fetch('/api/offline/manifest', { cache: 'no-store' });
      } catch (e) {
        if (e.message === 'aborted') throw e;
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
            const r = await fetch(
              '/api/offline/doc?file=' + encodeURIComponent(job.file), { cache: 'no-store' });
            if (r.status === 401) throw new Error('auth_required');
            if (!r.ok) throw new Error('doc_fetch_failed');
            const payload = await r.json();
            await this.saveDoc(user, job.file, job.hash, payload);
            for (const asset of extractAssetPaths(payload.html || '')) {
              check();
              if (onAsset) {
                // 素材镜像：读成 dataURL 交给调用方；失败退化为仅预热缓存
                try {
                  const imgRes = await fetch(asset, { cache: 'no-store' });
                  if (imgRes.ok) {
                    await onAsset(asset, await blobToDataURL(await imgRes.blob()));
                    continue;
                  }
                } catch (e) { /* 网络瞬断：走下方预热兜底 */ }
              }
              await fetch(asset).catch(() => { /* 素材缺失离线时显示裂图，不阻塞 */ });
            }
          } catch (e) {
            if (signal && signal.aborted) { fatal = fatal || new Error('aborted'); break; }
            if (e.message === 'auth_required') {
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

    /* 供页面侧镜像流程从 payload 提取素材路径（sw.js 的 docStrategy 亦内部使用） */
    extractAssetPaths,
  };

  globalThis.LibryOffline = API;
})();
