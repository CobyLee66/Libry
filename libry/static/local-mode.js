/* Libry 本地模式垫片——客户端壳内离线打开完整 Web 应用时生效。
   壳构建把 libry/static 快照打进 ui/webapp/（相对路径资产），该脚本被构建步骤
   注入到 app.js 之前：劫持 window.fetch，把 /api/* 请求改由壳 origin 的
   IndexedDB 镜像库（libry-offline，由 bridge.html 镜像维护）应答——
   离线时的页面、交互与在线完全同款，数据面本地化。

   生效条件：location.origin 含 tauri（壳内）。浏览器/服务器 origin 上本脚本
   不激活，一切保持在线行为。v1 边界：只读——除阅读进度本地生效外，
   其余写操作返回 offline_readonly（恢复网络后在完整应用中进行）。 */
(function () {
  'use strict';
  if (!/tauri/i.test(location.origin)) return;
  if (window.__libryLocalMode) return;
  window.__libryLocalMode = true;

  const state = { user: '', snapshot: null };
  let initPromise = null;

  function ensureInit() {
    if (!initPromise) {
      initPromise = (async () => {
        if (!window.LibryOffline) return;
        try {
          state.user = await LibryOffline.currentUser();
          if (!state.user) {
            // 无镜像库（未在线下载过）：回壳门户——门户会对空库禁用离线入口
            location.replace('../index.html');
            return;
          }
          state.snapshot = await LibryOffline.getSnapshot(state.user);
        } catch (e) { /* 读不到快照按无快照处理 */ }
      })();
    }
    return initPromise;
  }
  ensureInit();

  const jsonRes = (body, status = 200) => new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });

  /* ---------- /api/docs 语义（对齐服务端：status 过滤 + counts + 分页） ---------- */

  function statusFilter(items, status) {
    if (status === 'read') return items.filter((d) => d.read);
    if (status === 'unread') return items.filter((d) => !d.read);
    if (status === 'new') return items.filter((d) => d.is_new);
    return items;
  }

  function applyFilters(items, q) {
    const f = q;
    let out = items;
    if (f.q) {
      const needle = f.q.toLowerCase();
      out = out.filter((d) =>
        (d.title || '').toLowerCase().includes(needle)
        || ((d.summary || '') + '').toLowerCase().includes(needle));
    }
    if (f.type) out = out.filter((d) => d.type === f.type);
    if (f.visibility) out = out.filter((d) => d.visibility === f.visibility);
    if (f.tags && f.tags.length) {
      out = out.filter((d) => f.tags.every((tg) => (d.tags || []).includes(tg)));
    }
    if (f.date_from) out = out.filter((d) => (d.created || '') >= f.date_from);
    if (f.date_to) out = out.filter((d) => (d.created || '') <= f.date_to);
    return out;
  }

  function sortItems(items, sort, order) {
    const desc = order !== 'asc';
    const cmp = (a, b) => {
      if (sort === 'title') {
        return String(a.title || a.file).localeCompare(String(b.title || b.file), 'zh');
      }
      const ka = String(a[sort] || '');
      const kb = String(b[sort] || '');
      return ka.localeCompare(kb);
    };
    return items.slice().sort((a, b) => (desc ? -cmp(a, b) : cmp(a, b)));
  }

  function serveDocs(u) {
    const snap = state.snapshot;
    const p = u.searchParams;
    const status = p.get('status') || 'all';
    const all = snap && snap.docs ? snap.docs.items : [];
    const counts = (snap && snap.docs && snap.docs.counts)
      || { all: all.length, new: 0, unread: 0, read: 0 };
    const statusItems = statusFilter(all, status);
    const filtered = applyFilters(statusItems, {
      q: p.get('q') || '', tags: (p.get('tags') || '').split(',').filter(Boolean),
      type: p.get('type') || '', date_from: p.get('date_from') || '', date_to: p.get('date_to') || '',
      visibility: p.get('visibility') || '',
    });
    const total = filtered.length;
    const sort = p.get('sort') || 'created';
    const sorted = sortItems(filtered, sort, p.get('order') || '');
    const pageSize = Math.min(200, Math.max(1, parseInt(p.get('page_size') || '50', 10) || 50));
    const pageNum = Math.max(1, parseInt(p.get('page') || '1', 10) || 1);
    const start = (pageNum - 1) * pageSize;
    return jsonRes({
      total, page: pageNum, page_size: pageSize, counts,
      items: sorted.slice(start, start + pageSize),
    });
  }

  /* ---------- 阅读进度的本地持久化（IDB payload + 快照统计自洽） ---------- */

  async function storeLocalProgress(file, scroll, pct) {
    try {
      const rec = await LibryOffline.getDoc(state.user, file);
      if (rec && rec.payload) {
        rec.payload.progress = { scroll: scroll | 0, pct, updated_at: new Date().toISOString() };
        await LibryOffline.saveDoc(state.user, file, rec.hash, rec.payload);
      }
    } catch (e) { /* 正文未下载：仅更新快照 */ }
    try {
      const snap = state.snapshot;
      if (!snap) return;
      const nowIso = new Date().toISOString();
      const item = (snap.docs && snap.docs.items || []).find((i) => i.file === file);
      if (snap.meta && item) {
        snap.meta.continue_reading = { file, title: item.title, pct };
      }
      if (snap.marks && snap.marks.progress) {
        const entry = snap.marks.progress.find((pe) => pe.file === file);
        if (entry) { entry.pct = pct; entry.pos_updated_at = nowIso; }
      }
      await LibryOffline.saveSnapshot(state.user, snap);
    } catch (e) { /* 快照更新失败不影响应答 */ }
  }

  async function markLocalRead(file) {
    try {
      const snap = state.snapshot;
      if (!snap || !snap.docs) return;
      const item = (snap.docs.items || []).find((i) => i.file === file);
      if (item && !item.read) {
        item.read = true;
        const c = snap.docs.counts;
        if (c) { c.unread = Math.max(0, (c.unread || 0) - 1); c.read = (c.read || 0) + 1; }
        await LibryOffline.saveSnapshot(state.user, snap);
      }
    } catch (e) { /* 统计自洽失败不影响应答 */ }
  }

  /* ---------- fetch 劫持 ---------- */

  const nativeFetch = window.fetch.bind(window);

  async function shimApi(url, init) {
    const u = new URL(url, 'http://x/');
    const path = u.pathname;
    const method = (init && init.method) || 'GET';

    if (path === '/api/session') {
      return jsonRes({ authenticated: !!state.user, username: state.user, admin: false });
    }
    if (path === '/api/meta') {
      return jsonRes(state.snapshot && state.snapshot.meta
        ? state.snapshot.meta
        : { tag_groups: {}, standard_tags: [], types: [], date_range: { min: '', max: '' },
            stats: { total: 0, unread: 0, new: 0 }, generated_at: '', continue_reading: null });
    }
    if (path === '/api/docs') {
      return serveDocs(u);
    }
    if (path === '/api/doc') {
      const file = u.searchParams.get('file') || '';
      const rec = await LibryOffline.getDoc(state.user, file).catch(() => null);
      if (!rec) return jsonRes({ detail: 'doc_not_found' }, 404);
      markLocalRead(file);
      return jsonRes(rec.payload);
    }
    if (path === '/api/bookmarks') {
      const snap = state.snapshot;
      const data = (snap && snap.bookmarks)
        || { items: [], facet: {}, total: 0 };
      const tag = u.searchParams.get('tag');
      if (tag) {
        const items = data.items.filter((i) => (i.bookmark_tags || []).includes(tag));
        return jsonRes({ items, facet: data.facet, total: items.length });
      }
      return jsonRes(data);
    }
    if (path === '/api/marks') {
      return jsonRes((state.snapshot && state.snapshot.marks) || { progress: [], marks: [] });
    }
    if (path === '/api/graph') {
      const file = u.searchParams.get('file');
      return file
        ? jsonRes({ nodes: [], edges: [], center: file })
        : jsonRes({ nodes: [], edges: [], generated_at: '' });
    }
    if (path === '/api/state/progress' && method === 'POST') {
      let body = {};
      try { body = JSON.parse(init && init.body || '{}'); } catch (e) { /* 缺省体 */ }
      if (body.file) await storeLocalProgress(body.file, body.scroll, body.pct);
      return jsonRes({ ok: true });
    }
    // 其余写操作：本地模式 v1 只读
    return jsonRes({ detail: 'offline_readonly' }, 503);
  }

  window.fetch = function (input, init) {
    try {
      const url = typeof input === 'string' ? input : (input && input.url) || '';
      const path = url.replace(/^https?:\/\/[^/]+/i, '');
      if (path.startsWith('/api/') && !path.startsWith('/api/offline/')) {
        return ensureInit().then(() => shimApi(path, init));
      }
    } catch (e) { /* 解析失败走原生 */ }
    return nativeFetch(input, init);
  };

  /* ---------- 正文站内图片 → 镜像 dataURL ---------- */

  const observer = new MutationObserver(async () => {
    if (!state.user) return;
    const imgs = document.querySelectorAll('.markdown-body img[src]');
    for (let i = 0; i < imgs.length; i++) {
      const raw = imgs[i].getAttribute('src') || '';
      if (!raw || raw.startsWith('data:')) continue;
      try {
        const u = new URL(raw, 'http://x/');
        if (!u.pathname.startsWith('/raw/assets/')) continue;
        const dataURL = await LibryOffline.getAsset(state.user, u.pathname + u.search);
        if (dataURL) imgs[i].setAttribute('src', dataURL);
      } catch (e) { /* 非法 src 保持原样 */ }
    }
  });
  window.addEventListener('DOMContentLoaded', () => {
    observer.observe(document.body, { childList: true, subtree: true });
  });
})();
