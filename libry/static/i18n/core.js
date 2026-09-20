/* Libry i18n 运行时 — 手写轻量实现（无构建、无外部依赖；须在 vue.global.prod.js 与各 locale 文件之后加载）。
   能力：
   - 语言检测：localStorage['kb-lang']（手动选择过）→ 浏览器语言 zh* → 'zh-CN'，其余回退 'en'；
     自动检测不写 localStorage，跟随浏览器；仅手动切换（setLang）才持久化。
   - 响应式：state 由 Vue.reactive 包装，模板/计算属性里的 t() 调用读取 state.lang，
     切换语言即自动重渲染（含全局注册的子组件，组件内同样以 methods.t 暴露）。
   - t(key, params)：点路径查找 → 当前语言 → 'en' 兜底 → 返回 key 本身；
     {name} 占位符插值；值可为 {one, other} 复数对象（Intl.PluralRules 按 params.n 选择）。
   新增语言三步：i18n/ 下加 <code>.js 字典 → index.html 加 <script> 标签 → detect() 加浏览器语言映射。
   详见 docs/frontend-style.md。 */
(function () {
  const FALLBACK = 'en';
  const STORAGE_KEY = 'kb-lang';

  /* locale 注册表延迟读取（与 locale 文件的加载顺序无关） */
  const registry = () => window.LibryLocales || {};

  function lookup(locale, key) {
    let cur = locale;
    for (const part of key.split('.')) {
      if (cur === null || typeof cur !== 'object') return undefined;
      cur = cur[part];
    }
    return cur;
  }

  function detect() {
    const locales = registry();
    let saved = null;
    try { saved = localStorage.getItem(STORAGE_KEY); } catch (e) { /* 隐私模式等存储不可用 */ }
    if (saved && locales[saved]) return saved;
    const nav = (navigator.languages && navigator.languages.length)
      ? navigator.languages : [navigator.language || ''];
    for (const l of nav) {
      if (/^zh/i.test(l)) return 'zh-CN';
    }
    return FALLBACK;
  }

  const state = Vue.reactive({ lang: detect() });

  function t(key, params) {
    const locales = registry();
    let val = lookup(locales[state.lang], key);
    if (val === undefined) val = lookup(locales[FALLBACK], key);
    if (val === undefined) return key;
    if (val && typeof val === 'object') {
      /* 复数对象：{one, other}（或更多类别），按 params.n 选择 */
      const n = params && params.n;
      const cat = (typeof Intl !== 'undefined' && Intl.PluralRules)
        ? new Intl.PluralRules(state.lang).select(n)
        : (n === 1 ? 'one' : 'other');
      val = val[cat] || val.other;
    }
    if (params && typeof val === 'string') {
      val = val.replace(/\{(\w+)\}/g, (m, k) => (Object.prototype.hasOwnProperty.call(params, k) ? String(params[k]) : m));
    }
    return val;
  }

  /* 当前语言或回退语言中是否存在该 key（不回退到 key 本身） */
  function has(key) {
    const locales = registry();
    return lookup(locales[state.lang], key) !== undefined
      || lookup(locales[FALLBACK], key) !== undefined;
  }

  function applySideEffects() {
    document.documentElement.lang = state.lang;
    document.title = t('app.title');
  }

  function setLang(lang) {
    if (!registry()[lang]) return;
    state.lang = lang;
    try { localStorage.setItem(STORAGE_KEY, lang); } catch (e) { /* 存储不可用时仅本次会话生效 */ }
    applySideEffects();
  }

  /* 语言切换器选项：[{code, name}]，name 取各字典 _meta.name（本地语言名） */
  function langs() {
    return Object.keys(registry()).map((code) => ({
      code,
      name: lookup(registry()[code], '_meta.name') || code,
    }));
  }

  applySideEffects();
  window.LibryI18n = { state, t, has, setLang, langs, detect };
})();
