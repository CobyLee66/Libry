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
    star: '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
    'star-filled': '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" fill="currentColor" stroke="none"/>',
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
    download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
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

  /* 离线管理页「已下载文档」列表分页大小：只影响界面展示，数据仍完整存于 IndexedDB */
  const OFFLINE_PAGE_SIZE = 100;

  /* 离线写队列白名单：这些端点离线失败时入 outbox（offline.js），恢复在线自动回放；
     其余写操作（登录/改密/账户管理等）离线时直接报错不入队 */
  const OUTBOX_PATHS = ['/api/state/', '/api/marks', '/api/bookmarks', '/api/visibility', '/api/deletions'];
  /* LWW 写端点：离线回放时注入原始动作时间 updated_at（服务端参与跨端 LWW 比较） */
  const LWW_PATHS = ['/api/state/progress', '/api/marks', '/api/bookmarks', '/api/visibility'];

  let _vm = null;          // api() 向 Vue 实例同步离线状态用
  let _currentUser = '';   // 离线写队列的归属账户（登录后由 afterSessionKnown 写入）

  function isImeComposing(e) {
    // 中文输入法组词中的按键（keyCode 229 兼容旧 WebView）是 IME 操作，不是提交意图
    return e.isComposing || e.keyCode === 229;
  }

  /* 离线网络错误：带 .offline 标记，调用方（ensureSession/loadDoc/reloadList）据此
     走本地离线库兜底，与 404/429 等业务错误区分 */
  function offlineError() {
    const e = new Error(LibryI18n.t('err.offline'));
    e.offline = true;
    return e;
  }

  /* SW 就绪竞速：navigator.serviceWorker.ready 在无 SW 的环境（本地模式、不支持）
     会永久 pending，直接 await 会让后续流程静默卡死——必须带超时兜底 */
  async function swReady(timeoutMs = 3000) {
    try {
      return await Promise.race([
        navigator.serviceWorker.ready,
        new Promise((res) => setTimeout(() => res(null), timeoutMs)),
      ]);
    } catch (e) {
      return null;
    }
  }

  async function api(path, options = {}) {
    const opts = { headers: {}, ...options };
    const method = opts.method || 'GET';
    const rawBody = opts.body && typeof opts.body !== 'string' ? opts.body : null;
    if (opts.body && typeof opts.body !== 'string') {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(opts.body);
    }
    let res;
    try {
      res = await fetch(path, opts);
      // SW 缓存回放的成功响应不代表在线：离线标志跟随系统连通性，
      // 避免断网时每次缓存命中都把「离线模式」横幅熄灭
      if (_vm) _vm.offline = !navigator.onLine;
    } catch (e) {
      if (_vm) _vm.offline = true;
      if (method !== 'GET' && rawBody !== null
          && OUTBOX_PATHS.some((p) => path.startsWith(p)) && window.LibryOffline) {
        await LibryOffline.enqueueWrite({
          url: path, method, body: rawBody,
          ts: new Date().toISOString(), user: _currentUser,
        });
        if (_vm) _vm.outboxCount = await LibryOffline.outboxCount(_currentUser);
        throw new Error(LibryI18n.t('err.offlineQueued'));
      }
      throw offlineError();
    }
    if (res.status === 401) {
      location.hash = '#/login';
      throw new Error('unauthorized');
    }
    if (!res.ok) {
      let msg = LibryI18n.t('err.requestFailed', { status: res.status });
      let detail = '';
      try {
        const d = (await res.json()).detail;
        // 服务端错误码（见 docs/api.md）映射为当前语言文案；未识别的 detail 原样显示（兼容旧版/动态消息）
        if (d) {
          detail = d;
          msg = LibryI18n.has('api.' + d) ? LibryI18n.t('api.' + d) : d;
        }
      } catch (e) { /* ignore */ }
      // SW 离线且无缓存的合成 503 同样标记为离线错误（fetch 正常 resolve，不进上面的 catch）
      const err = new Error(msg);
      if (detail === 'offline_not_cached') err.offline = true;
      throw err;
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

  /* 客户端壳首页地址：壳连接页跳转时经 ?_libryHome= 传入并持久化，
     供设置页「断开连接并更换服务器」跳回壳页；纯浏览器访问没有该值（按钮隐藏）。
     只接受 http(s)/tauri 协议，防止异常值流入跳转目标。 */
  const SHELL_HOME_KEY = 'libry-shell-home';
  const SHELL_HOME_RE = /^(https?|tauri):\/\//i;
  function readShellHome() {
    try {
      const v = localStorage.getItem(SHELL_HOME_KEY);
      return v && SHELL_HOME_RE.test(v) ? v : '';
    } catch (e) { return ''; }
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
        docBarHidden: false,      // 窄屏阅读页：向下滚动时收起顶栏按钮行
        bookmarks: { items: [], facet: {}, total: 0 },
        bmFilterTag: '',
        bmLoading: false,
        bmEditor: null,           // { file, title, tags:[当前], draft, suggestions:[] }
        marksData: { progress: [], marks: [] },  // 书签页：自动阅读进度 + 手动书签
        marksLoading: false,
        toast: '',
        offline: false,           // 离线模式（navigator.onLine 或 API 网络失败时置位，缓存回放）
        outboxCount: 0,           // 离线写队列待同步条数
        offlineView: {            // 离线管理页状态
          busy: false, error: '', lastFailed: [],
          docs: [], page: 1, manifest: null, usage: null, lastSync: '', docsBytes: 0,
          progress: { done: 0, total: 0 },
          mirror: null,           // 壳内离线阅读器镜像进度 {done, total}（仅壳环境有值）
        },
        confirmBox: null,         // 通用确认弹层 {text, onOk}（替代原生 confirm，按钮可本地化）
        offlineScrollable: false,  // 已下载表格是否有溢出，决定是否显示自定义滚动条
        swUnavailable: false,     // SW 注册失败/不支持（HTTP 等非安全上下文）：重启后无法离线拉起
        sync: { syncing: false, error: '' },
        syncStatus: null,
        deletions: { items: [] },
        purge: { running: false, error: '' },
        purgeStatus: null,
        pw: { old: '', next: '', confirm: '', error: '', ok: false, changing: false },
        shellHome: '',            // 客户端壳首页地址（壳跳转时经 _libryHome 传入；纯浏览器访问为空）
        serverOrigin: location.origin,
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
        _debounce: null, _lastScrollY: 0,
        _progTimer: null, _pendingProg: null,  // 阅读进度上报：防抖定时器 + 待上报负载
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
      offlinePct() {
        const p = this.offlineView.progress;
        return p.total ? Math.round((p.done / p.total) * 100) : 0;
      },
      /* 已下载列表分页：当前页号自动夹在 1..总页数，避免文档增减后停在空页 */
      offlinePageCount() {
        return Math.max(1, Math.ceil(this.offlineView.docs.length / OFFLINE_PAGE_SIZE));
      },
      offlinePage() {
        return Math.min(Math.max(1, this.offlineView.page), this.offlinePageCount);
      },
      offlinePageDocs() {
        const start = (this.offlinePage - 1) * OFFLINE_PAGE_SIZE;
        return this.offlineView.docs.slice(start, start + OFFLINE_PAGE_SIZE);
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
      _vm = this;
      // 壳接入标记：壳连接页每次连接都带上自身首页地址，存储后从地址栏剥掉（保留 hash 深链）
      try {
        const u = new URL(location.href);
        const home = u.searchParams.get('_libryHome');
        if (home && SHELL_HOME_RE.test(home)) localStorage.setItem(SHELL_HOME_KEY, home);
        if (u.searchParams.has('_libryHome')) {
          u.searchParams.delete('_libryHome');
          history.replaceState(null, '', u.pathname + u.search + u.hash);
        }
      } catch (e) { /* URL/localStorage 不可用时忽略，按无壳处理 */ }
      this.shellHome = readShellHome();
      window.addEventListener('hashchange', () => this.route());
      // 离线状态：监听系统连通性事件；离线恢复在线时自动回放 outbox
      window.addEventListener('online', () => this.onConnectivityChange(true));
      window.addEventListener('offline', () => this.onConnectivityChange(false));
      if (!navigator.onLine) this.offline = true;
      if (window.LibryOffline) LibryOffline.outboxCount().then((n) => { this.outboxCount = n; });
      // 阅读页滚动方向决定顶栏按钮行收起/展开（仅窄屏有视觉效果）
      window.addEventListener('scroll', this.onDocScroll, { passive: true });
      // 窗口尺寸变化（旋转/拖拽宽度）时重绘画布，避免图形拉伸或留白
      window.addEventListener('resize', () => {
        clearTimeout(this._rsz);
        this._rsz = setTimeout(() => {
          if (this.view === 'doc' && this.relGraphData) this.renderRelGraph();
          if (this.view === 'graph') this.renderGlobalGraph();
          if (this.view === 'offline') this.updateOfflineScrollbar();
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
        this.flushProgress();  // 离开阅读页前补报一次阅读进度
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
        } else if (hash.startsWith('#/marks')) {
          const ok = await this.ensureSession();
          if (!ok) return;
          this.view = 'marks';
          await this.loadMarks();
        } else if (hash.startsWith('#/offline')) {
          const ok = await this.ensureSession();
          if (!ok) return;
          this.view = 'offline';
          await this.loadOfflinePage();
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
          // 每次进入都重取：continue_reading 卡片与新增计数需反映最新进度。
          // 离线时 meta 不可用（继续阅读卡片随之隐藏），不能阻断列表的离线回放
          try { await this.loadMeta(); } catch (e) { /* 离线：沿用旧 meta 或置空 */ }
          await this.reloadList(false);
        }
      },

      async ensureSession() {
        try {
          const res = await fetch('/api/session');
          const s = await res.json();
          if (!res.ok) {
            // 401 = 服务器可达但会话无效 → 登录；其余非 ok（含 SW 离线合成的 503
            // offline_not_cached，fetch 不 reject）→ 当作网络不可达，走下面的离线兜底
            if (res.status === 401) { this.view = 'login'; location.hash = '#/login'; return false; }
            throw new Error('session_unreachable');
          }
          if (!s.authenticated) { this.view = 'login'; location.hash = '#/login'; return false; }
          this.user = { name: s.username, admin: !!s.admin };
          await this.afterSessionKnown();
          return true;
        } catch (e) {
          // 网络不可达且无缓存会话：有离线库的账户以离线模式进入（读本地缓存内容）
          if (window.LibryOffline) {
            const cached = await LibryOffline.currentUser();
            if (cached) {
              this.user = { name: cached, admin: false };
              this.offline = true;
              await this.afterSessionKnown();
              return true;
            }
          }
          this.offline = !navigator.onLine;
          this.view = 'login';
          return false;
        }
      },

      async afterSessionKnown() {
        // 会话归属确认后：登记离线库当前用户（SW 缓存/回放按它隔离），并趁在线回放积压写操作
        _currentUser = this.user.name;
        if (!window.LibryOffline) return;
        await LibryOffline.setCurrentUser(this.user.name);
        this.outboxCount = await LibryOffline.outboxCount(_currentUser);
        if (navigator.onLine && this.outboxCount) await this.flushOutbox();
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
          this.offline = false;
          location.hash = '#/list';
          this.view = 'list';
          await this.afterSessionKnown();
          await this.loadMeta();
          await this.reloadList(false);
        } catch (e) {
          this.loginError = e.message === 'unauthorized' ? this.t('err.invalidCredentials') : e.message;
        } finally {
          this.loggingIn = false;
        }
      },

      async doLogout() {
        // 本地模式（壳内快照应用）：垫片无真实会话可注销，登出即回壳门户
        if (window.__libryLocalMode && this.shellHome) {
          this.disconnectServer();
          return;
        }
        try { await api('/api/logout', { method: 'POST' }); } catch (e) { /* 离线登出也继续清理本地 */ }
        const prevUser = _currentUser;
        _currentUser = '';
        this.meta = null; this.items = []; this.doc = null;
        this.bookmarks = { items: [], facet: {}, total: 0 };
        this.bmFilterTag = ''; this.bmEditor = null; this.toast = '';
        this.marksData = { progress: [], marks: [] };
        clearTimeout(this._progTimer); this._pendingProg = null;
        this.user = { name: '', admin: false }; this.users = [];
        this.offline = !navigator.onLine; this.outboxCount = 0;
        this.offlineView = { busy: false, error: '', lastFailed: [], docs: [],
                             page: 1, manifest: null, usage: null, lastSync: '', docsBytes: 0,
                             progress: { done: 0, total: 0 }, mirror: null };
        this.offlineScrollable = false;
        // 离线库按账户清理：文档缓存与清单快照随登出删除（outbox 保留待本人再登录回放）
        if (window.LibryOffline && prevUser) {
          try {
            await LibryOffline.setCurrentUser(null);
            await LibryOffline.dropDocs(prevUser);
            await LibryOffline.dropAssets(prevUser);
            await LibryOffline.saveManifest(prevUser, null);
            await LibryOffline.saveSnapshot(prevUser, null);
          } catch (e) { /* 本地清理失败不阻断登出 */ }
          try {
            const reg = await swReady();
            if (reg && reg.active) reg.active.postMessage({ type: 'clear-api-cache' });
          } catch (e) { /* SW 未就绪时忽略 */ }
          // 壳内镜像同步清理（尽力而为；失败时下次镜像按 ack 增量重建）
          await this.mirrorClearShell(prevUser).catch(() => {});
        }
        location.hash = '#/login';
        this.view = 'login';
      },

      /* 断开连接并更换服务器（仅客户端壳内可见）：注销会话后跳回壳的连接页。
         不清理离线库——IndexedDB 按服务器 origin 隔离，切回旧服务器时缓存仍在。
         壳页收到 _libryDisconnected 标记后保留地址记忆但不再自动连接。 */
      async disconnectServer() {
        if (!this.shellHome) return;
        try { await fetch('/api/logout', { method: 'POST' }); } catch (e) { /* 离线时尽力而为 */ }
        location.replace(this.shellHome + '?_libryDisconnected=1');
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
        } catch (e) {
          // 离线兜底：SW 缓存未命中时用离线库渲染可浏览列表（无已读状态/摘要，
          // 筛选支持 q/type/visibility/tags 与排序；counts 以总数近似，标签页徽标不展示）
          const rows = await this.offlineListRows(e);
          if (rows) {
            this.items = rows;
            this.total = rows.length;
            this.counts = { all: rows.length, new: 0, unread: 0, read: 0 };
          }
        } finally {
          this.loading = false;
        }
      },

      /* 断网时从离线库构造可浏览列表；返回 null 表示无离线数据（列表保持空态） */
      async offlineListRows(err) {
        if (!((err && err.offline) || !navigator.onLine)) return null;
        if (!window.LibryOffline) return null;
        const user = await LibryOffline.currentUser().catch(() => '');
        if (!user) return null;
        let saved;
        try { saved = await LibryOffline.listDocs(user); } catch (e) { return null; }
        const f = this.filters;
        const q = (f.q || '').toLowerCase();
        const docs = saved.map((r) => ({ file: r.file, ...((r.payload && r.payload.meta) || {}) }))
          .filter((d) => {
            if (f.type && d.type !== f.type) return false;
            if (f.visibility && d.visibility !== f.visibility) return false;
            if (f.tags.length && !f.tags.every((tg) => (d.tags || []).includes(tg))) return false;
            if (q && !((d.title || '').toLowerCase().includes(q))) return false;
            return true;
          });
        const key = f.sort === 'updated' ? 'updated' : f.sort === 'title' ? 'title' : 'created';
        docs.sort((a, b) => key === 'title'
          ? String(a.title || a.file).localeCompare(String(b.title || b.file), 'zh')
          : String(b[key] || '').localeCompare(String(a[key] || '')));
        return docs;
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
          this.openConfirm(this.t('doc.markConfirm'), async () => {
            try {
              await api('/api/deletions', { method: 'POST', body: { file } });
              this.doc.meta.marked_deleted = true;
              this.showToast(this.t('doc.markedToast'));
            } catch (e) { this.showToast(e.message); }
          });
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
        this.openConfirm(this.t('purge.confirm', { n: this.deletions.items.length }), async () => {
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
            try { if (this.meta) await this.loadMeta(); } catch (e) { /* 统计刷新失败不掩盖主流程 */ }
          }
        });
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
        this.openConfirm(this.t('users.deleteConfirm', { name: username }), async () => {
          try {
            const data = await api('/api/users/' + encodeURIComponent(username), { method: 'DELETE' });
            this.users = data.users;
          } catch (e) {
            alert(e.message);
          }
        });
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
        this.docBarHidden = false;
        this._lastScrollY = 0;
        clearTimeout(this._progTimer); this._pendingProg = null;
        try {
          this.doc = await api('/api/doc?file=' + encodeURIComponent(file));
        } catch (e) {
          // 离线兜底：SW 未注册/缓存未命中时直接读离线库
          // （payload 与 /api/doc 同构：服务端 _doc_payload 同一渲染管线产出）
          const cached = await this.offlineDoc(file, e);
          if (cached) {
            this.doc = cached;
          } else {
            alert(e.message);
            this.backToList();
            return;
          }
        }
        this.$nextTick(() => {
          const p = this.doc && this.doc.progress;
          if (p && (p.pct > 0 || p.scroll > 0)) {
            // 恢复上次阅读位置：优先按百分比（跨视口尺寸更稳），退化用像素
            const range = document.documentElement.scrollHeight - window.innerHeight;
            window.scrollTo(0, range > 0 ? Math.round(p.pct * range) : (p.scroll || 0));
            this.showToast(this.t('marks.restored'));
          } else {
            window.scrollTo(0, 0);
          }
          this.buildToc();
        });
        this.loadRelGraph(file);
      },

      /* 断网时回放离线库中已下载的文档；SW 在场时通常由 docStrategy 直接回放，走不到这里 */
      async offlineDoc(file, err) {
        if (!((err && err.offline) || !navigator.onLine)) return null;
        if (!window.LibryOffline) return null;
        const user = await LibryOffline.currentUser().catch(() => '');
        if (!user) return null;
        const rec = await LibryOffline.getDoc(user, file).catch(() => null);
        if (rec) this.offline = true;
        return rec ? rec.payload : null;
      },

      onDocScroll() {
        // 窄屏阅读页：累计方向位移超过阈值才收起/展开，忽略惯性停止时的细碎反向事件
        const y = Math.max(0, window.scrollY);
        if (this.view === 'doc') {
          const dy = y - this._lastScrollY;
          if (y < 24) {
            this.docBarHidden = false;
            this._lastScrollY = y;
          } else if (dy > 12 && y > 48) {
            // 24–48px 是顶部缓冲区，不在此处自动收起，避免与顶部强制展开相互触发
            this.docBarHidden = true;
            this._lastScrollY = y;
          } else if (dy < -12) {
            this.docBarHidden = false;
            this._lastScrollY = y;
          }
          this.reportProgress();
        }
      },

      currentPos() {
        // 当前滚动位置：像素 + 百分比（占可滚动区间；区间不存在视为 1=已读完）
        const range = document.documentElement.scrollHeight - window.innerHeight;
        const y = Math.max(0, Math.round(window.scrollY));
        return { scroll: y, pct: range > 0 ? Math.min(1, y / range) : 1 };
      },

      reportProgress() {
        // 滚动停止 ~1.5s 后防抖上报阅读进度（fire-and-forget，丢失可在下次滚动自愈）
        if (this.view !== 'doc' || !this.doc) return;
        const pos = this.currentPos();
        this._pendingProg = { file: this.doc.meta.file, scroll: pos.scroll, pct: pos.pct };
        clearTimeout(this._progTimer);
        this._progTimer = setTimeout(() => this.flushProgress(), 1500);
      },

      flushProgress() {
        // 立即上报待发的阅读进度（离开阅读页前调用；keepalive 保证页面切换不丢）
        clearTimeout(this._progTimer); this._progTimer = null;
        const p = this._pendingProg;
        if (!p) return;
        this._pendingProg = null;
        fetch('/api/state/progress', {
          method: 'POST', keepalive: true,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(p),
        }).catch(async () => {
          // 离线：入离线写队列（同 URL 待回放条目合并为最新，与服务端 LWW 语义一致）
          if (window.LibryOffline) {
            await LibryOffline.enqueueWrite({
              url: '/api/state/progress', method: 'POST',
              body: p, ts: new Date().toISOString(), user: _currentUser,
            });
            this.outboxCount = await LibryOffline.outboxCount(_currentUser);
            this.offline = true;
          }
        });
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
        try {
          await api('/api/state/unread', { method: 'POST', body: { files: [this.doc.meta.file] } });
        } catch (e) {
          // 离线时该写操作已入 outbox（提示「已暂存」）；其余失败也照常返回列表
          alert(e.message);
        }
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
        } catch (e) {
          // 静默会表现为「点了没反应」（本地模式只读等场景需要可见反馈）
          if (e && e.message && e.message !== 'unauthorized') this.showToast(e.message);
        }
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
        // IME 组词中的按键是输入法操作，不当作标签分隔（见 docs/frontend-style.md IME 章节）
        if (isImeComposing(e)) return;
        // 输入逗号/顿号即视为一个标签的结束
        if (e.key === ',' || e.key === '，' || e.key === '、') {
          e.preventDefault();
          this.addBmTag(this.bmEditor && this.bmEditor.draft);
        }
      },

      tagDraftEnter(e) {
        // IME 组词中的 Enter 是确认候选：不提交也不 preventDefault（拦截会卡死组词确认）
        if (isImeComposing(e)) return;
        e.preventDefault();
        this.addBmTag(this.bmEditor && this.bmEditor.draft);
      },

      graphSearchEnter(e) {
        // IME 组词中的 Enter 是确认候选，不触发定位
        if (isImeComposing(e)) return;
        this.locateGraphNode();
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

      // ---------------- 书签（阅读位置） ----------------

      openMarks() {
        location.hash = '#/marks';
      },

      async loadMarks() {
        this.marksLoading = true;
        try {
          this.marksData = await api('/api/marks');
        } finally {
          this.marksLoading = false;
        }
      },

      async toggleMark() {
        // 阅读页：在当前滚动位置添加书签；已有书签则更新到当前位置
        if (!this.doc) return;
        const file = this.doc.meta.file;
        const pos = this.currentPos();
        const existed = !!this.doc.marked;
        try {
          await api('/api/marks', {
            method: 'POST',
            body: { file, scroll: pos.scroll, pct: pos.pct },
          });
          this.doc.marked = true;
          this.showToast(this.t(existed ? 'marks.updated' : 'marks.saved'));
        } catch (e) { this.showToast(e.message); }
      },

      async removeMark(file) {
        try {
          await api('/api/marks', { method: 'DELETE', body: { file } });
          if (this.doc && this.doc.meta.file === file) this.doc.marked = false;
          this.showToast(this.t('marks.removed'));
          await this.loadMarks();
        } catch (e) { this.showToast(e.message); }
      },

      async clearProgress(file) {
        // 书签页：手动清除一条自动阅读进度（同时刷新列表页「继续阅读」卡片数据）
        try {
          await api('/api/state/progress', { method: 'DELETE', body: { file } });
          this.showToast(this.t('marks.progressCleared'));
          await this.loadMarks();
          if (this.meta) await this.loadMeta();
        } catch (e) { this.showToast(e.message); }
      },

      // ---------------- 离线模式（离线阅读 + 写操作回放） ----------------

      openOffline() {
        location.hash = '#/offline';
      },

      /* 自定义滚动条：原生滚动条在移动端/overlay 模式下常常不可见，按比例绘制轨道滑块。
         滚动时直接写滑块 style，避免 100 行表格每个 scroll 事件都走 Vue 重渲染。 */
      updateOfflineScrollbar() {
        const el = this.$refs.offlineTable;
        if (!el) return;
        const max = el.scrollHeight - el.clientHeight;
        if (max <= 1) {
          this.offlineScrollable = false;
          return;
        }
        this.offlineScrollable = true;
        const thumb = this.$refs.offlineScrollThumb;
        if (!thumb) {
          this.$nextTick(() => {
            if (this.view === 'offline') this.updateOfflineScrollbar();
          });
          return;
        }
        const height = Math.min(
          el.clientHeight,
          Math.max(24, Math.round((el.clientHeight * el.clientHeight) / el.scrollHeight)));
        const top = Math.round((el.clientHeight - height) * (el.scrollTop / max));
        thumb.style.top = top + 'px';
        thumb.style.height = height + 'px';
      },

      changeOfflinePage(delta) {
        const next = this.offlinePage + delta;
        if (next < 1 || next > this.offlinePageCount) return;
        this.offlineView.page = next;
        this.$nextTick(() => {
          const table = this.$refs.offlineTable;
          if (table) table.scrollTop = 0;
          this.updateOfflineScrollbar();
          const el = this.$refs.offlineList;
          if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
      },

      async loadOfflinePage() {
        const v = this.offlineView;
        if (!window.LibryOffline) return;
        // SW 状态在 index.html 注册时置位（pending 期间不误报）
        this.swUnavailable = window.__librySW === 'unavailable';
        v.page = 1;
        try {
          const rows = await LibryOffline.listDocs(this.user.name);
          const manifest = await LibryOffline.getManifest(this.user.name);
          // 文档数据字节数（IDB 内 payload 求和）：即时准确；usage 的 estimate 由
          // 浏览器配额系统惰性回收，清除后短时间不回落，两个数字分工展示
          const stats = await LibryOffline.docStats(this.user.name).catch(() => null);
          v.docsBytes = stats ? stats.bytes : 0;
          v.docs = rows.map((r) => {
            const meta = (r.payload && r.payload.meta) || {};
            const created = meta.created ? String(meta.created) : '';
            const updated = meta.updated ? String(meta.updated) : '';
            return {
              file: r.file,
              title: meta.title || r.file,
              size: r.size || 0,
              // 表格不显示日期，但排序仍按文章时间（优先创建时间）倒序
              sortTs: created || updated || '',
            };
          }).sort((a, b) => (b.sortTs || '').localeCompare(a.sortTs || '')
            || a.title.localeCompare(b.title, 'zh'));
          v.manifest = manifest;
          v.lastSync = manifest ? manifest.generated_at : '';
          if (navigator.storage && navigator.storage.estimate) {
            const est = await navigator.storage.estimate();
            v.usage = { usage: est.usage || 0, quota: est.quota || 0 };
          }
          this.$nextTick(() => {
            const table = this.$refs.offlineTable;
            if (table) table.scrollTop = 0;
            this.updateOfflineScrollbar();
          });
        } catch (e) { /* IDB 不可用等：页面显示空态 */ }
      },

      async downloadOffline() {
        if (!window.LibryOffline) return;
        const v = this.offlineView;
        v.busy = true; v.error = ''; v.lastFailed = [];
        v.progress = { done: 0, total: 0 };
        try {
          const r = await LibryOffline.syncContent(this.user.name, {
            onProgress: (p) => { v.progress = p; },
            // 素材镜像：抓到的图片存离线库 assets，供壳内离线阅读器断网渲染
            onAsset: (path, dataURL) => LibryOffline.saveAsset(this.user.name, path, dataURL),
          });
          v.lastFailed = r.failed || [];
          this.showToast(this.t('offline.done', { n: r.downloaded, removed: r.removed }));
        } catch (e) {
          v.error = LibryI18n.has('offlineErr.' + e.message)
            ? this.t('offlineErr.' + e.message) : (e.message || String(e));
        } finally {
          v.busy = false;
          await this.loadOfflinePage();
          // 镜像到壳内离线阅读器（仅壳环境；浏览器无壳自动跳过；失败静默——下次下载按 ack 增量补齐）
          await this.mirrorToShell(this.user.name,
            (done, total) => { v.mirror = { done, total }; });
          v.mirror = null;
        }
      },

      /* ---------- 壳内离线阅读器镜像（仅客户端壳环境） ----------
         远端页面无法直接写壳 origin 的 IndexedDB，经隐藏 iframe 加载壳资产 bridge.html
         postMessage 增量同步；桥回 ack 已存 hash 表，只发缺失/变化的篇目与素材。 */

      async _withShellBridge(fn, timeoutMs = 300000) {
        if (!this.shellHome || !window.LibryOffline) return false;
        const targetOrigin = this.shellHome.replace(/\/+$/, '');
        return await new Promise((resolve) => {
          const iframe = document.createElement('iframe');
          iframe.style.display = 'none';
          let settled = false;
          let pendingResolve = null;
          const finish = (ok) => {
            if (settled) return;
            settled = true;
            clearTimeout(timer);
            window.removeEventListener('message', onMessage);
            iframe.remove();
            if (pendingResolve) pendingResolve(null);
            resolve(ok);
          };
          const nextMessage = () => new Promise((res) => { pendingResolve = res; });
          const timer = setTimeout(() => finish(false), timeoutMs);
          const onMessage = (e) => {
            if (settled || e.source !== iframe.contentWindow || !pendingResolve) return;
            const res = pendingResolve;
            pendingResolve = null;
            res(e.data || {});
          };
          window.addEventListener('message', onMessage);
          iframe.src = targetOrigin + '/bridge.html';
          document.body.appendChild(iframe);
          (async () => {
            try {
              for (;;) {
                const d = await nextMessage();
                if (d && d.type === 'libry-bridge-ready') break;
              }
              await fn({ send: (msg) => iframe.contentWindow.postMessage(msg, targetOrigin), nextMessage });
              // 等桥的收尾确认；桥内单条消息失败经 libry-mirror-error 上报（不中断，
              // 桥会继续处理完剩余消息），其余超时按成功收尾——下次镜像按 ack 增量对账自愈
              for (;;) {
                const d = await Promise.race([
                  nextMessage(),
                  new Promise((res) => setTimeout(() => res(null), 10000)),
                ]);
                if (!d) break;
                if (d.type === 'libry-bridge-done-ok') break;
                if (d.type === 'libry-mirror-error') {
                  console.warn('[libry-mirror] 桥内部分写入失败：', d.message);
                }
              }
              finish(true);
            } catch (e) {
              finish(false);
            }
          })();
        });
      },

      async mirrorToShell(user, onProgress) {
        return this._withShellBridge(async (bridge) => {
          const docs = await LibryOffline.listDocs(user);
          const manifest = await LibryOffline.getManifest(user);
          bridge.send({ type: 'libry-mirror-hello', user });
          let have = null;
          for (;;) {
            const d = await bridge.nextMessage();
            if (d && d.type === 'libry-mirror-ack') { have = d.have || {}; break; }
          }
          const todo = docs.filter((r) => have[r.file] !== r.hash);
          const sentFiles = new Set();
          const sentAssets = new Set();
          for (const r of todo) {
            bridge.send({ type: 'libry-mirror-doc', user, file: r.file, hash: r.hash, payload: r.payload });
            sentFiles.add(r.file);
            for (const path of LibryOffline.extractAssetPaths((r.payload && r.payload.html) || '')) {
              if (sentAssets.has(path)) continue;
              sentAssets.add(path);
              const dataURL = await LibryOffline.getAsset(user, path).catch(() => null);
              if (dataURL) bridge.send({ type: 'libry-mirror-asset', user, path, dataURL });
            }
            if (onProgress) onProgress(sentFiles.size, todo.length);
            await new Promise((res) => setTimeout(res, 0));  // 让出主线程，避免长任务卡 UI
          }
          bridge.send({ type: 'libry-mirror-manifest', user, manifest });
          // 状态快照：本地模式垫片应答 /api/* 的数据源（列表/收藏/书签/统计）。
          // 需要在线抓取；失败置 null（垫片退化为仅文档能力，下次镜像重试）
          const snapshot = await this.fetchStateSnapshot();
          bridge.send({ type: 'libry-mirror-snapshot', user, snapshot });
          bridge.send({ type: 'libry-mirror-current-user', user });
          // 对账基准 = 本地离线库全量（未变化的存量文档虽未重发，也不得被桥删掉）
          bridge.send({ type: 'libry-mirror-done', keep: docs.map((r) => r.file) });
        });
      },

      async mirrorClearShell(user) {
        return this._withShellBridge(async (bridge) => {
          bridge.send({ type: 'libry-mirror-hello', user });
          for (;;) {
            const d = await bridge.nextMessage();
            if (d && d.type === 'libry-mirror-ack') break;
          }
          bridge.send({ type: 'libry-mirror-clear', user });
          bridge.send({ type: 'libry-mirror-done' });
        }, 15000);
      },

      /* 在线抓取列表/收藏/书签/统计的完整快照；失败返回 null（本地模式退化为仅文档能力） */
      async fetchStateSnapshot() {
        try {
          const pageSize = 200;
          let page = 1;
          let items = [];
          let counts = null;
          for (;;) {
            const p = new URLSearchParams({ page: String(page), page_size: String(pageSize), status: 'all' });
            const data = await api('/api/docs?' + p.toString());
            counts = data.counts;
            items = items.concat(data.items);
            if (items.length >= data.total || data.items.length === 0) break;
            page += 1;
          }
          const [meta, bookmarks, marks] = await Promise.all([
            api('/api/meta'), api('/api/bookmarks'), api('/api/marks'),
          ]);
          return {
            docs: { items, counts },
            meta,
            bookmarks,
            marks,
            saved_at: new Date().toISOString(),
          };
        } catch (e) {
          return null;
        }
      },

      /* ---------- 通用确认弹层（原生 confirm 的按钮文案无法本地化） ---------- */

      openConfirm(text, onOk) {
        this.confirmBox = { text, onOk };
      },

      closeConfirm() {
        this.confirmBox = null;
      },

      async applyConfirm() {
        const box = this.confirmBox;
        if (!box) return;
        this.confirmBox = null;
        try {
          await box.onOk();
        } catch (e) {
          // 弹窗已关，失败必须可见（此前静默吞掉会表现为「点了没反应」）
          this.showToast(e && e.message ? e.message : String(e));
        }
      },

      async clearOfflineData() {
        if (!window.LibryOffline) return;
        this.openConfirm(this.t('offline.clearConfirm'), async () => {
          const user = this.user.name;
          // 第一步：本地库清理（快速、阻塞界面反馈）——完成即刷新页面数据
          try {
            const destroyed = await LibryOffline.destroyIfOnlyUser(user);
            if (!destroyed) {
              await LibryOffline.dropDocs(user);
              await LibryOffline.dropAssets(user);
              await LibryOffline.saveManifest(user, null);
              await LibryOffline.saveSnapshot(user, null);
            }
          } catch (e) {
            // IDB 被旧连接阻塞等失败必须可见（静默会表现为「点了没反应」）
            this.showToast(e && e.message === 'idb_blocked'
              ? this.t('offlineErr.idb_blocked') : (e && e.message || String(e)));
            return;
          }
          this.showToast(this.t('offline.cleared'));
          await this.loadOfflinePage();
          // 第二步（后台尽力而为，不阻塞界面）：素材缓存与壳内镜像清理。
          // 整库压缩回收已在第一步完成（无其他账户数据时），占用数字随首次刷新回落
          try {
            const reg = await swReady();
            if (reg && reg.active) reg.active.postMessage({ type: 'clear-asset-cache' });
          } catch (e) { /* SW 未就绪时忽略 */ }
          await this.mirrorClearShell(user).catch(() => {});
        });
      },

      async onConnectivityChange(isOnline) {
        this.offline = !isOnline;
        if (isOnline) await this.flushOutbox();
      },

      async flushOutbox() {
        if (!window.LibryOffline) return;
        try {
          if (!_currentUser) {
            this.outboxCount = await LibryOffline.outboxCount();
            return;  // 未登录不回放（回放需要会话）
          }
          const r = await LibryOffline.replayOutbox(_currentUser, (item) => {
            const body = this.replayBody(item);
            return fetch(item.url, {
              method: item.method,
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(body),
            });
          });
          this.outboxCount = r.remaining;
          if (r.auth_expired) {
            this.showToast(this.t('offline.reloginNeeded'));
            location.hash = '#/login';
          } else if (r.replayed) {
            this.showToast(this.t('offline.synced', { n: r.replayed }));
          }
        } catch (e) { /* 本地队列读取失败（如 DB 升级阻塞）：留待下次在线事件重试 */ }
      },

      replayBody(item) {
        // LWW 写端点回放时注入原始动作时间：离线变更与在线多端变更按动作时间正确合并
        // （服务端 coerce_updated_at 参与比较，未来值钳制，旧客户端不带该字段行为不变）
        if (!item.body || !LWW_PATHS.some((p) => item.url.startsWith(p))) return item.body;
        return { ...item.body, updated_at: item.body.updated_at || item.ts };
      },

      fmtBytes(n) {
        if (n === null || n === undefined) return '';
        const units = ['B', 'KB', 'MB', 'GB'];
        let v = n, i = 0;
        while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
        return (i === 0 ? v : v.toFixed(1)) + ' ' + units[i];
      },

      fmtPct(p) {
        return Math.round((p || 0) * 100) + '%';
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
