# API 一览

所有接口由 `libry/server/main.py` 提供；除登录与 webhook 外均需会话（`kb_session` 签名 cookie，7 天）。

| 接口 | 说明 |
|---|---|
| `POST /api/login` / `POST /api/logout` | 用户名+密码登录（限速 5 次/分/IP）/ 登出 |
| `GET /api/session` | 当前会话：authenticated / username / admin |
| `POST /api/password` | 修改自己的密码（校验当前密码，限速） |
| `GET/POST /api/users`、`DELETE /api/users/{name}` | 账户管理（仅管理员；删除写墓碑防跨端复活） |
| `GET /api/meta` | 标签分组、类型、日期范围、统计（总数/未读/新增，按当前账户**可见**文档） |
| `GET /api/docs` | 列表：`q`（标题/摘要子串）、`tags`（逗号分隔，AND）、`type`、`date_from/to`、`visibility=all\|shared\|personal`、`status=all\|new\|unread\|read`、`sort=created\|updated\|title`、`page`；个人文档仅所有者与管理员可见 |
| `GET /api/doc?file=` | 渲染 HTML + 元数据 + 上下篇 + 相关页面（related，需 graph.json）；打开自动标记已读；对无权者返回 404（与不存在不可区分） |
| `GET /api/graph` | 全库关联图：nodes（title/type/tags）+ edges（[a, b, weight]）；无 graph.json 返回空；节点/边按当前用户可见性过滤 |
| `GET /api/graph?file=` | 局部关联图：中心文档 + 一跳邻居节点 + 节点间边（阅读页「相关页面」图） |
| `POST /api/visibility` | 切换文档个人/共享（body: `{"file", "visibility": "shared"\|"personal"}`）；权限 = 当前用户可见即可切换，personal 归属当前用户 |
| `GET /api/deletions` | 待删除标记列表（仅管理员），含 file/title/marked_by/marked_at/exists |
| `POST /api/deletions` / `DELETE /api/deletions` | 标记 / 取消标记删除（body: `{"file"}`，仅管理员） |
| `POST /api/deletions/execute` | 立即批量清理（仅管理员，限速，后台执行返回 202）：purge →（KB_ROLE=primary 再跑 publish.sh）→ sync-data → 热重载 |
| `GET /api/deletions/status` | 上次清理结果（`.libry/purge-status.json`） |
| `POST /api/state/read` / `unread` | 批量标记（body: `{"files": [...]}`，按当前账户） |
| `POST /api/state/ack-new` | （已废弃，前端不再调用）推进「新增」水位 |
| `POST /api/reindex` | 重建索引（session 或 `X-Sync-Secret` 二选一） |
| `POST /api/sync` | webhook（`X-Sync-Secret` 校验 + 限速，后台跑 deploy/sync.sh，返回 202） |
| `POST /api/sync-data` | 手动触发用户数据同步（仅管理员，后台执行返回 202） |
| `POST /api/sync-data/reload` | 跨端同步写盘后热重载内存用户数据（`X-Sync-Secret`） |
| `GET /api/sync-data/status` | 上次数据同步结果（`.libry/sync-status.json`） |

**状态语义**（按账户）：未读 = 不在已读集合；新增 = `created` 晚于该账户首次登录水位且未读；水位在首次登录时固定、不再推进，文章只有标记已读后才移出新增列表。所有列表/统计均只含当前账户可见的文档（共享 + 自己的个人 + 管理员视角下的全部个人）。

**可见性语义**：frontmatter `visibility`/`owner` 是初始状态；Web 端切换后以 `.libry/visibility.json` 运行时覆盖层为准（LWW 跨端同步）。

**错误响应**：`HTTPException` 的 `detail` 为稳定错误码（snake_case），由 Web 前端按界面语言翻译展示（字典见 `libry/static/i18n/` 的 `api.*` 命名空间）；脚本消费者请按错误码判断，不要解析自然语言。错误码一览：

| 错误码 | 场景（状态码） |
|---|---|
| `rate_limited` | 登录/改密/清理/同步触发限速（429） |
| `invalid_credentials` | 登录用户名或密码错误（401） |
| `current_password_wrong` | 当前密码错误（401） |
| `password_too_short` | 密码不足 8 位（400） |
| `doc_not_found` / `file_not_found` | 文档不存在或无权访问（404） |
| `files_not_list` | `files` 参数不是数组（400） |
| `not_bookmarked` | 取消未收藏的文档（404） |
| `bad_visibility` | `visibility` 取值非法（400） |
| `invalid_sync_secret` | `X-Sync-Secret` 校验失败（403） |
| `user_not_found` / `user_exists` / `bad_username` | 账户管理（404/400） |
| `cannot_delete_self` / `cannot_delete_last_admin` | 删除账户约束（400） |
| `auth_required` / `admin_required` | 会话过期（401）/ 需管理员（403） |

**purge 状态**（`GET /api/deletions/status`，源 `.libry/purge-status.json`）：`result` ∈ `ok / empty / error`；`ok` 附结构化 `pages`（删除页数）与 `refs`（清理引用数）字段，前端按界面语言格式化展示；`error` 时 `detail` 为原始诊断输出（stderr 等），前端原样透出。
