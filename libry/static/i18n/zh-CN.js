/* Libry 界面文案 — 简体中文（zh-CN）。
   格式约定：赋值对象必须是严格 JSON（键双引号、无尾逗号、无注释），
   tests/test_i18n.py 依赖该格式做跨语言 key 一致性校验。
   新增语言的步骤见 docs/frontend-style.md。 */
window.LibryLocales = window.LibryLocales || {};
window.LibryLocales["zh-CN"] = {
  "_meta": { "name": "中文" },
  "app": { "title": "Libry · 书阁", "brand": "书阁", "logoAlt": "书阁图标" },
  "common": {
    "loading": "加载中…",
    "back": "← 返回",
    "logout": "退出登录",
    "close": "关闭",
    "save": "保存",
    "never": "从未",
    "admin": "管理员",
    "personal": "个人",
    "personalTitle": "个人文档",
    "personalWithTitle": "个人文档 · 所有者：{owner}",
    "language": "语言"
  },
  "login": {
    "username": "用户名",
    "password": "密码",
    "submit": "登录",
    "submitting": "登录中…"
  },
  "settings": { "title": "设置" },
  "pw": { "show": "显示密码", "hide": "隐藏密码" },
  "pwChange": {
    "title": "修改密码",
    "oldPlaceholder": "当前密码",
    "newPlaceholder": "新密码（至少 8 位）",
    "confirmPlaceholder": "确认新密码",
    "submit": "确认修改",
    "submitting": "提交中…",
    "ok": "密码已修改，下次登录生效",
    "tooShort": "新密码至少 8 位",
    "mismatch": "两次输入的新密码不一致"
  },
  "users": {
    "title": "账户管理",
    "delete": "删除",
    "namePlaceholder": "新用户名",
    "passwordPlaceholder": "密码（至少 8 位）",
    "add": "添加账户",
    "adding": "添加中…",
    "nameRequired": "请输入用户名",
    "passwordShort": "密码至少 8 位",
    "deleteConfirm": "确定删除账户「{name}」？其阅读状态会保留但无法再登录。"
  },
  "sync": {
    "title": "数据同步",
    "desc": "统一账户、已读历史与收藏夹到 GitHub，并在本机与 VPS 之间双向同步。",
    "lastRun": "上次同步：{ts}（{result}）",
    "trigger": "立即同步",
    "syncing": "同步中…",
    "started": "已触发数据同步"
  },
  "syncResult": {
    "pushed": "已推送",
    "no changes": "无变更",
    "dry-run": "试运行",
    "skipped": "已跳过",
    "error": "失败"
  },
  "purge": {
    "title": "待删除页面",
    "desc": "在阅读页点删除图标标记的页面，会在下次定时入库时批量删除（同时清理其他页面对它们的引用），也可立即手动执行。",
    "empty": "暂无待删除页面",
    "stale": "已失效",
    "staleTitle": "文件已不在库中，清理时将直接核销标记",
    "unmark": "取消删除标记",
    "lastRun": "上次清理：{ts}（{result}）",
    "execute": "立即执行删除（{n}）",
    "running": "执行中…",
    "done": "清理完成",
    "failed": "清理失败",
    "okSummary": "删除 {pages} 个页面，清理引用 {refs} 处",
    "confirm": "确定立即删除这 {n} 个标记页面？\n将删除文件并清理其他页面对它们的引用，变更会提交推送到 GitHub，不可撤销。"
  },
  "purgeResult": { "ok": "完成", "empty": "无待删除", "error": "失败" },
  "doc": {
    "dates": "创建 {created} · 更新 {updated}",
    "markedBanner": "本页面已标记待删除，将在下次定时清理时被删除（含其他页面对它的引用）。",
    "bookmark": "收藏",
    "unbookmark": "取消收藏",
    "markUnread": "标为未读",
    "markRead": "标为已读",
    "setShared": "设为共享",
    "setPersonal": "设为个人",
    "markDelete": "标记删除",
    "markedBadge": "已标记待删除",
    "markConfirm": "标记后将在下次定时清理时删除该页面（含其他页面对它的引用）。确定标记？",
    "relatedTitle": "相关页面",
    "relOpen": "展开关联图",
    "relClose": "收起关联图",
    "toc": "目录",
    "nowPersonal": "已设为个人文档",
    "nowShared": "已设为共享文档",
    "markedToast": "已标记待删除",
    "unmarkedToast": "已取消删除标记"
  },
  "bm": {
    "title": "收藏夹",
    "all": "全部",
    "empty": "暂无收藏，去文章页点收藏图标试试",
    "addedAt": "收藏于 {date}",
    "editTags": "编辑标签",
    "remove": "取消收藏",
    "removedToast": "已取消收藏",
    "tagsSaved": "标签已保存"
  },
  "bmEditor": {
    "title": "收藏标签",
    "removeTag": "移除标签",
    "placeholder": "输入标签，回车或逗号添加",
    "suggest": "建议标签"
  },
  "graph": {
    "title": "知识图谱",
    "searchPlaceholder": "定位节点（回车）…",
    "allTags": "全部标签",
    "notFound": "未找到匹配节点",
    "emptyPre": "关联图数据未生成。请在本地运行",
    "emptyPost": "后发布同步。",
    "tooltip": "{title}（{type}）"
  },
  "list": {
    "searchPlaceholder": "搜索标题 / 摘要…",
    "filter": "筛选",
    "empty": "没有匹配的文档",
    "loadMore": "加载更多（{n}/{total}）",
    "whoami": "当前账户：{name}",
    "filterTag": "筛选标签：{tag}"
  },
  "status": { "all": "全部", "new": "新增", "unread": "未读", "read": "已读" },
  "filters": {
    "allTypes": "全部类型",
    "allVisibility": "全部可见性",
    "byVisibility": "按个人/共享筛选",
    "shared": "共享",
    "dateFrom": "创建日期起",
    "dateTo": "创建日期止",
    "sortCreated": "按创建时间",
    "sortUpdated": "按更新时间",
    "sortTitle": "按标题",
    "clear": "清空筛选"
  },
  "type": { "sources": "资料", "entities": "实体", "concepts": "概念", "synthesis": "综合", "archive": "原文" },
  "err": {
    "requestFailed": "请求失败（{status}）",
    "invalidCredentials": "用户名或密码错误",
    "adminRequired": "需要管理员权限"
  },
  "api": {
    "rate_limited": "尝试过于频繁，请稍后再试",
    "invalid_credentials": "用户名或密码错误",
    "current_password_wrong": "当前密码错误",
    "password_too_short": "密码至少 8 位",
    "doc_not_found": "文档不存在",
    "file_not_found": "文件不存在",
    "files_not_list": "files 必须是数组",
    "not_bookmarked": "尚未收藏该文档",
    "bad_visibility": "visibility 必须是 shared 或 personal",
    "invalid_sync_secret": "无效的 X-Sync-Secret",
    "user_not_found": "用户不存在",
    "bad_username": "用户名仅限字母、数字、- _ .",
    "user_exists": "用户名已存在",
    "cannot_delete_self": "不能删除当前登录账户",
    "cannot_delete_last_admin": "不能删除唯一的管理员",
    "auth_required": "未登录或会话已过期",
    "admin_required": "需要管理员权限"
  }
};
