/* Libry（书阁）知识库 Web 前端 — Vue 3（自托管）单页应用，无构建步骤。
   路由：#/login、#/list?<query>、#/doc/<urlencoded file>
   界面文案一律经 i18n/core.js（window.LibryI18n）的 t() 取用，不在模板/代码里硬编码。 */
(function () {
  const { createApp } = Vue;

  /* 密码可见性切换：眼睛/斜线眼睛图标（Feather 风格） */
  const EyeIcon = {
    props: { on: { type: Boolean, default: false } },
    emits: ['toggle'],
    template: `
      <button type="button" class="pw-toggle"
              :title="on ? t('pw.hide') : t('pw.show')"
              :aria-label="on ? t('pw.hide') : t('pw.show')"
              @click="$emit('toggle')">
        <svg v-if="!on" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
        </svg>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
          <line x1="1" y1="1" x2="23" y2="23"/>
        </svg>
      </button>`,
    methods: {
      t(key, params) { return LibryI18n.t(key, params); },
    },
  };

  /* 通用 Feather 风格图标（与 EyeIcon 同源，stroke=currentColor） */
  const ICON_PATHS = {
    bookmark: '<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>',
    'bookmark-filled': '<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" fill="currentColor" stroke="none"/>',
    x: '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    'trash-2': '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/>',
    'edit-3': '<path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>',
    list: '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>',
    filter: '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>',
    settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
    'share-2': '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>',
    'log-out': '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
    lock: '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    unlock: '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/>',
    eye: '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
    'eye-off': '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>',
  };
  const IconIcon = {
    props: { name: { type: String, required: true } },
    template: `
      <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
           aria-hidden="true" v-html="ICON_PATHS[name]"></svg>`,
    data() { return { ICON_PATHS }; },
  };

  const DEFAULT_FILTERS = () => ({
    q: '', tags: [], type: '', date_from: '', date_to: '',
    visibility: '', status: 'all', sort: 'created',
  });

  async function api(path, options = {}) {
    const opts = { headers: {}, ...options };
    if (opts.body && typeof opts.body !== 'string') {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(opts.body);
    }
    const res = await fetch(path, opts);
    if (res.status === 401) {
      location.hash = '#/login';
      throw new Error('unauthorized');
    }
    if (!res.ok) {
      let msg = LibryI18n.t('err.requestFailed', { status: res.status });
      try {
        const d = (await res.json()).detail;
        // 服务端错误码（见 docs/api.md）映射为当前语言文案；未识别的 detail 原样显示（兼容旧版/动态消息）
        if (d) msg = LibryI18n.has('api.' + d) ? LibryI18n.t('api.' + d) : d;
      } catch (e) { /* ignore */ }
      throw new Error(msg);
    }
    return res.json();
  }

  /* 关联图：节点配色取自 style.css 的 CSS 变量（canvas 无法直接引用变量） */
  function cssVar(name, fallback) {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
  }
  function typeColors() {
    return {
      sources: cssVar('--primary', '#2563eb'),
      concepts: cssVar('--unread', '#f59e0b'),
      entities: cssVar('--new', '#ef4444'),
      synthesis: cssVar('--muted', '#8a8f99'),
      archive: cssVar('--archive', '#0d9488'),
    };
  }

  /* 展示层标签（类型/同步/清理结果）经 i18n 字典翻译（type.* / syncResult.* / purgeResult.*），
     底层值保持英文目录名/状态码不变 */

  const app = createApp({
    data() {
      return {
        view: 'loading',          // loading | login | list | doc | settings
        loginUser: '', password: '', loggingIn: false, loginError: '',
        show: { login: false, old: false, next: false, confirm: false, add: false },
        user: { name: '', admin: false },
        users: [],
        newUser: { name: '', password: '', admin: false, error: '', adding: false },
        meta: null,
        filters: DEFAULT_FILTERS(),
        showFilters: false,
        items: [], total: 0, page: 1, pageSize: 50,
        counts: { all: 0, new: 0, unread: 0, read: 0 },
        loading: false,
        doc: null,
        toc: [], showToc: false,
        bookmarks: { items: [], facet: {}, total: 0 },
        bmFilterTag: '',
        bmLoading: false,
        bmEditor: null,           // { file, title, tags:[当前], draft, suggestions:[] }
        toast: '',
        sync: { syncing: false, error: '' },
        syncStatus: null,
        deletions: { items: [] },
        purge: { running: false, error: '' },
        purgeStatus: null,
        pw: { old: '', next: '', confirm: '', error: '', ok: false, changing: false },
        graphTypes: ['sources', 'entities', 'concepts', 'synthesis', 'archive'],
        relGraphData: null,       // 阅读页局部关联图 {nodes, edges, center}
        relGraphOpen: false,      // 窄屏展开关联图
        relTip: { show: false, x: 0, y: 0, text: '' },
        gview: {
          loading: false, loaded: false, nodes: [], edges: [],
          q: '', tag: '', types: { sources: true, entities: true, concepts: true, synthesis: true, archive: true },
        },
        gTip: { show: false, x: 0, y: 0, text: '' },
        _gsim: null, _gdraw: null, _gt: null, _glocated: '',
        _debounce: null,
      };
    },
    computed: {
      /* 语言切换器：v-model 代理到 LibryI18n（手动 setLang 才写 localStorage） */
      lang: {
        get() { return LibryI18n.state.lang; },
        set(v) { LibryI18n.setLang(v); },
      },
      langs() { return LibryI18n.langs(); },
      statusTabs() {
        return ['all', 'new', 'unread', 'read'].map((key) => ({ key, label: this.t('status.' + key) }));
      },
      /* 设置页「上次清理」补充文案：ok 用结构化页数/引用数格式化，error 透出诊断 detail */
      purgeDetailText() {
        return this.fmtPurgeDetail(this.purgeStatus);
      },
      visibleTagGroups() {
        if (!this.meta) return {};
        const groups = {};
        for (const [name, tags] of Object.entries(this.meta.tag_groups)) {
          if (name.includes('类型标签')) continue; // 类型由目录决定，用类型下拉筛选
          groups[name] = tags;
        }
        return groups;
      },
      activeFilterCount() {
        const f = this.filters;
        return f.tags.length + (f.type ? 1 : 0) + (f.date_from ? 1 : 0) + (f.date_to ? 1 : 0)
          + (f.visibility ? 1 : 0);
      },
      allGraphTags() {
        return this.meta ? (this.meta.standard_tags || []) : [];
      },
    },
    watch: {
      filters: {
        deep: true,
        handler() {
          clearTimeout(this._debounce);
          this._debounce = setTimeout(() => this.reloadList(), 250);
        },
      },
    },
    mounted() {
      window.addEventListener('hashchange', () => this.route());
      // 窗口尺寸变化（旋转/拖拽宽度）时重绘画布，避免图形拉伸或留白
      window.addEventListener('resize', () => {
        clearTimeout(this._rsz);
        this._rsz = setTimeout(() => {
          if (this.view === 'doc' && this.relGraphData) this.renderRelGraph();
          if (this.view === 'graph') this.renderGlobalGraph();
        }, 300);
      });
      this.route();
    },
    methods: {
      encodeURIComponent,

      t(key, params) {
        return LibryI18n.t(key, params);
      },

      typeLabel(ty) {
        return LibryI18n.has('type.' + ty) ? LibryI18n.t('type.' + ty) : ty;
      },

      fmtSyncResult(r) {
        return LibryI18n.has('syncResult.' + r) ? LibryI18n.t('syncResult.' + r) : r;
      },

      async route() {
        if (this._gsim) { this._gsim.stop(); this._gsim = null; }  // 离开图谱页停止布局仿真
        const hash = location.hash || '#/list';
        if (hash.startsWith('#/doc/')) {
          const ok = await this.ensureSession();
          if (!ok) return;
          this.view = 'doc';
          await this.loadDoc(decodeURIComponent(hash.slice(6)));
        } else if (hash.startsWith('#/graph')) {
          const ok = await this.ensureSession();
          if (!ok) return;
          this.view = 'graph';
          if (!this.meta) await this.loadMeta();
          await this.loadGlobalGraph();
        } else if (hash.startsWith('#/login')) {
          this.view = 'login';
        } else if (hash.startsWith('#/bookmarks')) {
          const ok = await this.ensureSession();
          if (!ok) return;
          this.view = 'bookmarks';
          await this.loadBookmarks();
        } else if (hash.startsWith('#/settings')) {
          const ok = await this.ensureSession();
          if (!ok) return;
          this.view = 'settings';
          if (this.user.admin && this.users.length === 0) this.loadUsers();
          if (this.user.admin) {
            this.loadSyncStatus();
            this.loadDeletions();
            this.loadPurgeStatus();
          }
        } else {
          const ok = await this.ensureSession();
          if (!ok) return;
          this.view = 'list';
          this.restoreFilters(hash);
          if (!this.meta) await this.loadMeta();
          await this.reloadList(false);
        }
      },

      async ensureSession() {
        try {
          const s = await fetch('/api/session').then(r => r.json());
          if (!s.authenticated) { this.view = 'login'; location.hash = '#/login'; return false; }
          this.user = { name: s.username, admin: !!s.admin };
          return true;
        } catch (e) { return false; }
      },

      async doLogin() {
        this.loggingIn = true; this.loginError = '';
        try {
          const res = await api('/api/login', {
            method: 'POST',
            body: { username: this.loginUser, password: this.password },
          });
          this.user = { name: res.username, admin: !!res.admin };
          this.password = '';
          location.hash = '#/list';
          this.view = 'list';
          await this.loadMeta();
          await this.reloadList(false);
        } catch (e) {
          this.loginError = e.message === 'unauthorized' ? this.t('err.invalidCredentials') : e.message;
        } finally {
          this.loggingIn = false;
        }
      },

      async doLogout() {
        try { await api('/api/logout', { method: 'POST' }); } catch (e) { /* ignore */ }
        this.meta = null; this.items = []; this.doc = null;
        this.bookmarks = { items: [], facet: {}, total: 0 };
        this.bmFilterTag = ''; this.bmEditor = null; this.toast = '';
        this.user = { name: '', admin: false }; this.users = [];
        location.hash = '#/login';
        this.view = 'login';
      },

      async loadMeta() {
        this.meta = await api('/api/meta');
        this.counts.new = this.meta.stats.new;
      },

      queryString() {
        const f = this.filters;
        const p = new URLSearchParams();
        if (f.q) p.set('q', f.q);
        if (f.tags.length) p.set('tags', f.tags.join(','));
        if (f.type) p.set('type', f.type);
        if (f.date_from) p.set('date_from', f.date_from);
        if (f.date_to) p.set('date_to', f.date_to);
        if (f.visibility) p.set('visibility', f.visibility);
        if (f.status !== 'all') p.set('status', f.status);
        if (f.sort !== 'created') p.set('sort', f.sort);
        return p.toString();
      },

      restoreFilters(hash) {
        // URL query 优先，其次 sessionStorage（从阅读页返回时保留筛选）
        const qi = hash.indexOf('?');
        const raw = qi >= 0 ? hash.slice(qi + 1) : (sessionStorage.getItem('kb-list-query') || '');
        const p = new URLSearchParams(raw);
        const f = DEFAULT_FILTERS();
        f.q = p.get('q') || '';
        f.tags = p.get('tags') ? p.get('tags').split(',') : [];
        f.type = p.get('type') || '';
        f.date_from = p.get('date_from') || '';
        f.date_to = p.get('date_to') || '';
        f.visibility = (p.get('visibility') === 'personal' || p.get('visibility') === 'shared')
          ? p.get('visibility') : '';
        f.status = p.get('status') || 'all';
        f.sort = p.get('sort') || 'created';
        const changed = JSON.stringify(f) !== JSON.stringify(this.filters);
        this.filters = f;
        return changed;
      },

      async reloadList(resetPage = true) {
        if (this.view !== 'list') return;
        if (resetPage) { this.page = 1; }
        const qs = this.queryString();
        sessionStorage.setItem('kb-list-query', qs);
        history.replaceState(null, '', '#/list' + (qs ? '?' + qs : ''));
        this.loading = true;
        try {
          const p = new URLSearchParams(qs);
          p.set('page', this.page);
          p.set('page_size', this.pageSize);
          const data = await api('/api/docs?' + p.toString());
          this.items = this.page === 1 ? data.items : this.items.concat(data.items);
          this.total = data.total;
          this.counts = data.counts;
        } finally {
          this.loading = false;
        }
      },

      loadMore() {
        this.page += 1;
        this.reloadList(false);
      },

      setStatus(key) {
        // 新增水位在首次登录时固定，不再推进；文章只有标记已读后才移出新增
        this.filters.status = key;
      },

      toggleTag(t) {
        const i = this.filters.tags.indexOf(t);
        if (i >= 0) this.filters.tags.splice(i, 1);
        else this.filters.tags.push(t);
      },

      filterByTag(t) {
        // 点击文章卡片上的标签：直接按该标签筛选（已在筛选中则取消）
        this.toggleTag(t);
      },

      openSettings() {
        this.pw = { old: '', next: '', confirm: '', error: '', ok: false, changing: false };
        this.newUser = { name: '', password: '', admin: false, error: '', adding: false };
        this.sync = { syncing: false, error: '' };
        this.purge = { running: false, error: '' };
        if (this.user.admin) {
          this.loadUsers();
          this.loadSyncStatus();
          this.loadDeletions();
          this.loadPurgeStatus();
        }
        location.hash = '#/settings';
      },

      async loadSyncStatus() {
        try {
          this.syncStatus = await api('/api/sync-data/status');
        } catch (e) { /* ignore */ }
      },

      async triggerSync() {
        this.sync.error = '';
        this.sync.syncing = true;
        try {
          await api('/api/sync-data', { method: 'POST' });
          this.showToast(this.t('sync.started'));
          setTimeout(() => this.loadSyncStatus(), 3000);
        } catch (e) {
          this.sync.error = e.message === 'unauthorized' ? this.t('err.adminRequired') : e.message;
        } finally {
          this.sync.syncing = false;
        }
      },

      fmtSyncTs(ts) {
        if (!ts) return LibryI18n.t('common.never');
        return String(ts).slice(0, 16).replace('T', ' ');
      },

      fmtPurgeResult(r) {
        return LibryI18n.has('purgeResult.' + r) ? LibryI18n.t('purgeResult.' + r) : r;
      },

      fmtPurgeDetail(st) {
        if (!st) return '';
        if (st.result === 'ok') {
          if (typeof st.pages === 'number') return this.t('purge.okSummary', { pages: st.pages, refs: st.refs || 0 });
          return st.detail || this.t('purge.done');  // 旧版状态文件仅有中文 detail
        }
        if (st.result === 'error') return st.detail || this.t('purge.failed');
        return st.detail || '';
      },

      // ---------------- 待删除标记（管理员） ----------------

      async loadDeletions() {
        try {
          this.deletions = await api('/api/deletions');
        } catch (e) { /* ignore */ }
      },

      async loadPurgeStatus() {
        try {
          this.purgeStatus = await api('/api/deletions/status');
        } catch (e) { /* ignore */ }
      },

      async toggleDeleteMark() {
        // 阅读页：标记/取消删除（图标按钮，仅管理员可见）
        if (!this.doc) return;
        const file = this.doc.meta.file;
        if (this.doc.meta.marked_deleted) {
          try {
            await api('/api/deletions', { method: 'DELETE', body: { file } });
            this.doc.meta.marked_deleted = false;
            this.showToast(this.t('doc.unmarkedToast'));
          } catch (e) { this.showToast(e.message); }
        } else {
          if (!confirm(this.t('doc.markConfirm'))) return;
          try {
            await api('/api/deletions', { method: 'POST', body: { file } });
            this.doc.meta.marked_deleted = true;
            this.showToast(this.t('doc.markedToast'));
          } catch (e) { this.showToast(e.message); }
        }
      },

      async unmarkDeletion(file) {
        try {
          await api('/api/deletions', { method: 'DELETE', body: { file } });
          this.showToast(this.t('doc.unmarkedToast'));
          await this.loadDeletions();
        } catch (e) { this.showToast(e.message); }
      },

      async executePurge() {
        if (!this.deletions.items.length) return;
        if (!confirm(this.t('purge.confirm', { n: this.deletions.items.length }))) return;
        this.purge.error = '';
        this.purge.running = true;
        const startedAt = new Date();
        try {
          await api('/api/deletions/execute', { method: 'POST' });
          // 后台执行（含 publish/graph 重建），轮询状态直到 last_run 越过触发时刻
          for (let i = 0; i < 100; i++) {
            await new Promise(r => setTimeout(r, 3000));
            const st = await api('/api/deletions/status');
            this.purgeStatus = st;
            if (st.last_run && new Date(st.last_run) >= startedAt) {
              if (st.result === 'ok' || st.result === 'empty') {
                this.showToast(this.fmtPurgeDetail(st) || this.t('purge.done'));
              } else {
                this.purge.error = this.fmtPurgeDetail(st) || this.t('purge.failed');
              }
              break;
            }
          }
        } catch (e) {
          this.purge.error = e.message === 'unauthorized' ? this.t('err.adminRequired') : e.message;
        } finally {
          this.purge.running = false;
          await this.loadDeletions();
          if (this.meta) await this.loadMeta();
        }
      },

      async loadUsers() {
        try {
          const data = await api('/api/users');
          this.users = data.users;
        } catch (e) { /* ignore */ }
      },

      async addUser() {
        this.newUser.error = '';
        if (!this.newUser.name) { this.newUser.error = this.t('users.nameRequired'); return; }
        if (this.newUser.password.length < 8) { this.newUser.error = this.t('users.passwordShort'); return; }
        this.newUser.adding = true;
        try {
          const data = await api('/api/users', {
            method: 'POST',
            body: { username: this.newUser.name, password: this.newUser.password, admin: this.newUser.admin },
          });
          this.users = data.users;
          this.newUser = { name: '', password: '', admin: false, error: '', adding: false };
        } catch (e) {
          this.newUser.error = e.message;
        } finally {
          this.newUser.adding = false;
        }
      },

      async deleteUser(username) {
        if (!confirm(this.t('users.deleteConfirm', { name: username }))) return;
        try {
          const data = await api('/api/users/' + encodeURIComponent(username), { method: 'DELETE' });
          this.users = data.users;
        } catch (e) {
          alert(e.message);
        }
      },

      async changePassword() {
        this.pw.error = ''; this.pw.ok = false;
        if (this.pw.next.length < 8) { this.pw.error = this.t('pwChange.tooShort'); return; }
        if (this.pw.next !== this.pw.confirm) { this.pw.error = this.t('pwChange.mismatch'); return; }
        this.pw.changing = true;
        try {
          await api('/api/password', {
            method: 'POST',
            body: { old_password: this.pw.old, new_password: this.pw.next },
          });
          this.pw.ok = true;
          this.pw.old = this.pw.next = this.pw.confirm = '';
        } catch (e) {
          this.pw.error = e.message === 'unauthorized' ? this.t('api.current_password_wrong') : e.message;
        } finally {
          this.pw.changing = false;
        }
      },

      clearFilters() {
        const status = this.filters.status;
        this.filters = { ...DEFAULT_FILTERS(), status };
      },

      async loadDoc(file) {
        this.doc = null;
        this.toc = [];
        this.showToc = false;
        this.relGraphData = null;
        this.relGraphOpen = false;
        try {
          this.doc = await api('/api/doc?file=' + encodeURIComponent(file));
          window.scrollTo(0, 0);
          this.$nextTick(() => this.buildToc());
          this.loadRelGraph(file);
        } catch (e) {
          alert(e.message);
          this.backToList();
        }
      },

      buildToc() {
        // 从渲染后的 markdown 中提取 h1-h3，生成可跳转的章节目录
        const root = document.querySelector('.markdown-body');
        if (!root) return;
        const list = [];
        root.querySelectorAll('h1, h2, h3').forEach((h, i) => {
          if (!h.id) h.id = 'toc-' + i;
          list.push({ id: h.id, text: h.textContent.trim(), level: Number(h.tagName[1]) });
        });
        this.toc = list;
      },

      jumpTo(id) {
        const el = document.getElementById(id);
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        this.showToc = false;
      },

      async markUnread() {
        if (!this.doc) return;
        await api('/api/state/unread', { method: 'POST', body: { files: [this.doc.meta.file] } });
        this.backToList();
      },

      async toggleRead(d) {
        // 卡片上手动切换已读/未读
        const path = d.read ? '/api/state/unread' : '/api/state/read';
        try {
          await api(path, { method: 'POST', body: { files: [d.file] } });
          d.read = !d.read;
          d.is_new = false;
          const delta = d.read ? 1 : -1;
          this.counts.read = Math.max(0, this.counts.read + delta);
          this.counts.unread = Math.max(0, this.counts.unread - delta);
        } catch (e) { /* ignore */ }
      },

      backToList() {
        const qs = sessionStorage.getItem('kb-list-query') || '';
        location.hash = '#/list' + (qs ? '?' + qs : '');
      },

      // ---------------- 收藏夹 ----------------

      openBookmarks() {
        location.hash = '#/bookmarks';
      },

      async loadBookmarks() {
        this.bmLoading = true;
        try {
          const qs = this.bmFilterTag ? '?tag=' + encodeURIComponent(this.bmFilterTag) : '';
          const data = await api('/api/bookmarks' + qs);
          this.bookmarks = data;
        } finally {
          this.bmLoading = false;
        }
      },

      setBmFilter(tag) {
        this.bmFilterTag = tag;
        this.loadBookmarks();
      },

      async toggleBookmark() {
        // 阅读页：收藏/取消收藏（图标按钮）
        if (!this.doc) return;
        const file = this.doc.meta.file;
        if (this.doc.meta.bookmarked) {
          try {
            await api('/api/bookmarks', { method: 'DELETE', body: { file } });
            this.doc.meta.bookmarked = false;
            this.doc.bookmark_tags = [];
            this.showToast(this.t('bm.removedToast'));
          } catch (e) { this.showToast(e.message); }
        } else {
          try {
            const res = await api('/api/bookmarks', { method: 'POST', body: { file, tags: [] } });
            this.doc.meta.bookmarked = true;
            this.doc.bookmark_tags = res.bookmark_tags || [];
            this.openBmEditor(file, this.doc.meta.title, this.doc.meta.tags, this.doc.bookmark_tags);
          } catch (e) { this.showToast(e.message); }
        }
      },

      async toggleVisibility() {
        // 阅读页：个人 ↔ 共享（图标按钮）。设为个人时归属当前账户。
        if (!this.doc) return;
        const file = this.doc.meta.file;
        const target = this.doc.meta.visibility === 'personal' ? 'shared' : 'personal';
        try {
          const res = await api('/api/visibility', {
            method: 'POST',
            body: { file, visibility: target },
          });
          this.doc.meta.visibility = res.visibility;
          this.doc.meta.owner = res.owner;
          this.showToast(res.visibility === 'personal' ? this.t('doc.nowPersonal') : this.t('doc.nowShared'));
        } catch (e) { this.showToast(e.message); }
      },

      editBookmarkTags(item) {
        // 收藏夹页：编辑该收藏的标签（item.tags 为文章标签，item.bookmark_tags 为收藏标签）
        this.openBmEditor(item.file, item.title, item.tags, item.bookmark_tags);
      },

      openBmEditor(file, title, articleTags, currentTags) {
        const current = (currentTags || []).slice();
        const seen = new Set(current);
        const suggestions = [];
        for (const t of [...(articleTags || []), ...Object.keys(this.bookmarks.facet || {})]) {
          if (!seen.has(t)) { suggestions.push(t); seen.add(t); }
        }
        this.bmEditor = { file, title, tags: current, draft: '', suggestions };
      },

      closeBmEditor() {
        this.bmEditor = null;
      },

      addBmTag(t) {
        t = (t || '').trim();
        if (!t || !this.bmEditor || this.bmEditor.tags.includes(t)) return;
        this.bmEditor.tags.push(t);
        this.bmEditor.draft = '';
      },

      removeBmTag(t) {
        if (!this.bmEditor) return;
        this.bmEditor.tags = this.bmEditor.tags.filter(x => x !== t);
      },

      handleTagDraft(e) {
        // 输入逗号/顿号即视为一个标签的结束
        if (e.key === ',' || e.key === '，' || e.key === '、') {
          e.preventDefault();
          this.addBmTag(this.bmEditor && this.bmEditor.draft);
        }
      },

      async saveBmTags() {
        if (!this.bmEditor) return;
        if (this.bmEditor.draft.trim()) this.addBmTag(this.bmEditor.draft);
        const { file, tags } = this.bmEditor;
        try {
          const res = await api('/api/bookmarks', { method: 'PUT', body: { file, tags } });
          if (this.doc && this.doc.meta.file === file) this.doc.bookmark_tags = res.bookmark_tags;
          this.bmEditor = null;
          this.showToast(this.t('bm.tagsSaved'));
          if (this.view === 'bookmarks') await this.loadBookmarks();
        } catch (e) { this.showToast(e.message); }
      },

      async removeBookmark(file) {
        try {
          await api('/api/bookmarks', { method: 'DELETE', body: { file } });
          if (this.doc && this.doc.meta.file === file) {
            this.doc.meta.bookmarked = false;
            this.doc.bookmark_tags = [];
          }
          this.showToast(this.t('bm.removedToast'));
          await this.loadBookmarks(); // 刷新列表与 facet
        } catch (e) { this.showToast(e.message); }
      },

      // ---------------- 关联图 ----------------

      openGraph() {
        location.hash = '#/graph';
      },

      async loadRelGraph(file) {
        // 阅读页局部关联图；图数据缺失时静默降级为只显示相关列表
        try {
          const data = await api('/api/graph?file=' + encodeURIComponent(file));
          if (!data.nodes || data.nodes.length < 2) return;
          this.relGraphData = data;
          // 桌面端由 CSS 强制展开；移动端默认折叠，点击展开时才渲染（容器 display:none 时宽度为 0）
          this.$nextTick(() => this.renderRelGraph());
        } catch (e) { /* ignore */ }
      },

      toggleRelGraph() {
        this.relGraphOpen = !this.relGraphOpen;
        if (this.relGraphOpen) this.$nextTick(() => this.renderRelGraph());
      },

      renderRelGraph() {
        const canvas = this.$refs.relCanvas;
        if (!canvas || !this.relGraphData || typeof d3 === 'undefined') return;
        const data = this.relGraphData;
        const W = canvas.parentElement.clientWidth, H = 300;
        if (!W) return;  // 容器未显示（移动端折叠中），展开时再渲染
        const dpr = window.devicePixelRatio || 1;
        canvas.width = W * dpr; canvas.height = H * dpr;
        canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
        const ctx = canvas.getContext('2d');
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        const colors = typeColors();
        const nodes = data.nodes.map(n => ({ ...n }));
        const links = data.edges.map(e => ({ source: e[0], target: e[1], w: e[2] }));
        const sim = d3.forceSimulation(nodes)
          .force('link', d3.forceLink(links).id(d => d.file)
            .distance(l => 130 - 70 * l.w).strength(l => 0.4 + l.w))
          .force('charge', d3.forceManyBody().strength(-220))
          .force('center', d3.forceCenter(W / 2, H / 2))
          .force('collide', d3.forceCollide(30))
          .stop();
        const center = nodes.find(n => n.file === data.center);
        if (center) { center.fx = W / 2; center.fy = H / 2; }
        for (let i = 0; i < 250; i++) sim.tick();  // 同步跑完布局，静态绘制
        for (const n of nodes) {  // 防溢出裁剪
          n.x = Math.max(16, Math.min(W - 16, n.x));
          n.y = Math.max(16, Math.min(H - 16, n.y));
        }
        const edgeColor = cssVar('--border', '#e5e7eb');
        const textColor = cssVar('--text', '#1f2329');
        ctx.clearRect(0, 0, W, H);
        for (const l of links) {
          ctx.strokeStyle = edgeColor;
          ctx.lineWidth = 0.6 + l.w * 3;
          ctx.beginPath();
          ctx.moveTo(l.source.x, l.source.y);
          ctx.lineTo(l.target.x, l.target.y);
          ctx.stroke();
        }
        for (const n of nodes) {
          const isCenter = n.file === data.center;
          ctx.fillStyle = colors[n.type] || colors.synthesis;
          ctx.beginPath();
          ctx.arc(n.x, n.y, isCenter ? 9 : 6, 0, 2 * Math.PI);
          ctx.fill();
          if (isCenter) {
            ctx.strokeStyle = cssVar('--primary', '#2563eb');
            ctx.lineWidth = 2;
            ctx.stroke();
          }
          ctx.fillStyle = textColor;
          ctx.font = '11px sans-serif';
          ctx.textAlign = 'center';
          const label = n.title.length > 12 ? n.title.slice(0, 12) + '…' : n.title;
          ctx.fillText(label, n.x, n.y + (isCenter ? 21 : 18));
        }
        const pick = (mx, my) => nodes.find(n => (n.x - mx) ** 2 + (n.y - my) ** 2 < 121);
        canvas.onclick = (ev) => {
          const r = canvas.getBoundingClientRect();
          const n = pick(ev.clientX - r.left, ev.clientY - r.top);
          if (n) location.hash = '#/doc/' + encodeURIComponent(n.file);
        };
        canvas.onmousemove = (ev) => {
          const r = canvas.getBoundingClientRect();
          const n = pick(ev.clientX - r.left, ev.clientY - r.top);
          canvas.style.cursor = n ? 'pointer' : 'default';
          this.relTip = n
            ? { show: true, x: n.x + 12, y: n.y - 10, text: n.title }
            : { show: false, x: 0, y: 0, text: '' };
        };
        canvas.onmouseleave = () => { this.relTip = { show: false, x: 0, y: 0, text: '' }; };
      },

      async loadGlobalGraph() {
        if (!this.gview.loaded) {
          this.gview.loading = true;
          try {
            const data = await api('/api/graph');
            this.gview.nodes = data.nodes || [];
            this.gview.edges = data.edges || [];
            this.gview.loaded = true;
          } catch (e) { this.showToast(e.message); }
          this.gview.loading = false;
        }
        this.$nextTick(() => this.renderGlobalGraph());
      },

      graphNodeVisible(n) {
        const v = this.gview;
        return !!(v.types[n.type] && (!v.tag || (n.tags || []).includes(v.tag)));
      },

      drawGlobalGraph() {
        if (this._gdraw) this._gdraw();
      },

      renderGlobalGraph() {
        const canvas = this.$refs.globalCanvas;
        if (!canvas || typeof d3 === 'undefined' || !this.gview.nodes.length) return;
        if (this._gsim) { this._gsim.stop(); this._gsim = null; }
        const W = canvas.parentElement.clientWidth;
        const H = Math.max(420, window.innerHeight - 170);
        const dpr = window.devicePixelRatio || 1;
        canvas.width = W * dpr; canvas.height = H * dpr;
        canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
        const ctx = canvas.getContext('2d');
        const colors = typeColors();
        const edgeColor = cssVar('--border', '#e5e7eb');
        const textColor = cssVar('--text', '#1f2329');
        const nodes = this.gview.nodes.map(n => ({ ...n }));
        const nodeByFile = {};
        nodes.forEach(n => { nodeByFile[n.file] = n; });
        const links = [];
        const degree = {};
        for (const e of this.gview.edges) {
          if (!nodeByFile[e[0]] || !nodeByFile[e[1]]) continue;
          links.push({ source: e[0], target: e[1], w: e[2] });
          degree[e[0]] = (degree[e[0]] || 0) + 1;
          degree[e[1]] = (degree[e[1]] || 0) + 1;
        }
        const radius = n => 3 + Math.min(degree[n.file] || 0, 14) * 0.5;
        // 重要节点（连接数前 8%，至少 12 个）：未放大时也显示文字；放大后显示全部标签
        const important = new Set(
          [...nodes].sort((a, b) => (degree[b.file] || 0) - (degree[a.file] || 0))
            .slice(0, Math.max(12, Math.round(nodes.length * 0.08)))
            .filter(n => (degree[n.file] || 0) > 0)
            .map(n => n.file),
        );

        this._gt = d3.zoomIdentity;
        const draw = () => {
          const t = this._gt;
          ctx.save();
          ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
          ctx.clearRect(0, 0, W, H);
          ctx.translate(t.x, t.y);
          ctx.scale(t.k, t.k);
          for (const l of links) {
            if (!this.graphNodeVisible(l.source) || !this.graphNodeVisible(l.target)) continue;
            ctx.globalAlpha = 0.2 + l.w * 0.5;
            ctx.strokeStyle = edgeColor;
            ctx.lineWidth = 0.4 + l.w * 1.8;
            ctx.beginPath();
            ctx.moveTo(l.source.x, l.source.y);
            ctx.lineTo(l.target.x, l.target.y);
            ctx.stroke();
          }
          ctx.globalAlpha = 1;
          const showAllLabels = t.k >= 1.6;
          for (const n of nodes) {
            if (!this.graphNodeVisible(n)) continue;
            ctx.fillStyle = colors[n.type] || colors.synthesis;
            ctx.beginPath();
            ctx.arc(n.x, n.y, radius(n), 0, 2 * Math.PI);
            ctx.fill();
            if (n.file === this._glocated) {
              ctx.strokeStyle = cssVar('--new', '#ef4444');
              ctx.lineWidth = 2.5 / t.k;
              ctx.stroke();
            }
            const isHub = important.has(n.file);
            if (showAllLabels || isHub) {
              // 重要节点带浅色描边底，缩小状态下也可读
              const fontPx = (isHub ? 12 : 11) / t.k;
              ctx.font = fontPx + 'px sans-serif';
              ctx.textAlign = 'center';
              const label = n.title.length > 14 ? n.title.slice(0, 14) + '…' : n.title;
              const ly = n.y + radius(n) + (isHub ? 12 : 11) / t.k;
              if (isHub) {
                ctx.strokeStyle = cssVar('--card', '#ffffff');
                ctx.lineWidth = 3 / t.k;
                ctx.strokeText(label, n.x, ly);
              }
              ctx.fillStyle = textColor;
              ctx.fillText(label, n.x, ly);
            }
          }
          ctx.restore();
        };
        this._gdraw = draw;

        const sim = d3.forceSimulation(nodes)
          .force('link', d3.forceLink(links).id(d => d.file)
            .distance(l => 90 - 50 * l.w).strength(l => l.w * 0.7))
          .force('charge', d3.forceManyBody().strength(-60))
          .force('center', d3.forceCenter(0, 0))
          .force('collide', d3.forceCollide(n => radius(n) + 2))
          .alphaDecay(0.03)
          .on('tick', draw);
        this._gsim = sim;
        this._gnodes = nodes;

        const worldAt = (ev) => {
          const r = canvas.getBoundingClientRect();
          const p = [ev.clientX - r.left, ev.clientY - r.top];
          return this._gt.invert(p);
        };
        const nodeAt = (ev) => {
          const [wx, wy] = worldAt(ev);
          return sim.find(wx, wy, 8 / this._gt.k + 5);
        };

        let dragged = false;
        const drag = d3.drag()
          .subject((ev) => {
            const [wx, wy] = this._gt.invert([ev.x, ev.y]);
            return sim.find(wx, wy, 8 / this._gt.k + 5);
          })
          .on('start', (ev) => {
            dragged = false;
            if (!ev.active) sim.alphaTarget(0.1).restart();
            ev.subject.fx = ev.subject.x;
            ev.subject.fy = ev.subject.y;
          })
          .on('drag', (ev) => {
            dragged = true;
            const [wx, wy] = this._gt.invert([ev.x, ev.y]);
            ev.subject.fx = wx;
            ev.subject.fy = wy;
          })
          .on('end', (ev) => {
            if (!ev.active) sim.alphaTarget(0);
            ev.subject.fx = null;
            ev.subject.fy = null;
          });

        const zoom = d3.zoom()
          .scaleExtent([0.15, 6])
          // 命中节点的拖动留给节点拖拽，空白处才 pan
          .filter((ev) => ev.type === 'wheel' || ev.type === 'dblclick' || !nodeAt(ev))
          .on('zoom', (ev) => { this._gt = ev.transform; draw(); });
        const sel = d3.select(canvas);
        sel.call(zoom).call(drag);
        sel.call(zoom.transform, d3.zoomIdentity.translate(W / 2, H / 2));
        sel.on('dblclick.zoom', null);  // 双击不放大，避免误触
        this._gzoom = { sel, zoom, W, H };

        canvas.onmousemove = (ev) => {
          const r = canvas.getBoundingClientRect();
          const n = nodeAt(ev);
          canvas.style.cursor = n ? 'pointer' : 'default';
          this.gTip = n && this.graphNodeVisible(n)
            ? { show: true, x: ev.clientX - r.left + 12, y: ev.clientY - r.top - 10,
                text: this.t('graph.tooltip', { title: n.title, type: this.typeLabel(n.type) }) }
            : { show: false, x: 0, y: 0, text: '' };
        };
        canvas.onmouseleave = () => { this.gTip = { show: false, x: 0, y: 0, text: '' }; };
        canvas.onclick = (ev) => {
          if (dragged) { dragged = false; return; }  // 拖拽抬手不跳转
          const n = nodeAt(ev);
          if (n) location.hash = '#/doc/' + encodeURIComponent(n.file);
        };
        draw();
      },

      locateGraphNode() {
        const q = (this.gview.q || '').toLowerCase();
        if (!q || !this._gsim || !this._gzoom) return;
        const n = (this._gnodes || []).find(x => x.title.toLowerCase().includes(q));
        if (!n) { this.showToast(this.t('graph.notFound')); return; }
        this._glocated = n.file;
        const { sel, zoom, W, H } = this._gzoom;
        const k = Math.max(this._gt.k, 2);
        sel.transition().duration(500).call(
          zoom.transform,
          d3.zoomIdentity.translate(W / 2 - n.x * k, H / 2 - n.y * k).scale(k),
        );
      },

      showToast(msg) {
        this.toast = msg;
        clearTimeout(this._toastTimer);
        this._toastTimer = setTimeout(() => { this.toast = ''; }, 2000);
      },
    },
  });
  app.component('pw-eye', EyeIcon);
  app.component('icon', IconIcon);
  app.mount('#app');
})();
