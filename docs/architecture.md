# 架构与数据流

## 双仓库模型

Libry 把「引擎」和「内容」拆成两个独立单元：

- **引擎**（本仓库）：Python 包 + 静态前端 + lint 工具 + 部署脚本。经 `pip install .` 安装，提供 `libry` CLI。
- **vault**（用户各自持有）：纯 markdown 知识库 + `libry.toml` 配置 + `.libry/` 运行数据，本身是 git 仓库。

引擎定位 vault 的方式（先者胜）：`--root` 参数 → `KB_ROOT` 环境变量 → 当前目录。

```
libry/
├── config.py            # 单一配置来源：libry.toml + env
├── __main__.py          # CLI（init/serve/index/graph/purge/sync-data/passwd/config/skills/lint）
├── indexer.py           # 扫描 vault → .libry/index.json（元数据）+ content.json（全文语料）
├── build_graph.py       # 可选：fastembed embedding + 结构信号 → graph.json
├── purge_marked.py      # 标记-清理两段式的执行端（机械引用清理）
├── sync_data.py         # 用户数据跨端 CRDT 同步（LWW + 墓碑）
├── server/              # FastAPI：auth/render/state/bookmarks/visibility/deletions/main
├── static/              # Vue 3（vendored）单页前端，无构建步骤
└── templates/vault/     # libry init 的脚手架源（AGENTS.md + skills + 示例内容）
```

## 索引与检索

`libry index` 扫描 `wiki/{sources,entities,concepts,synthesis}/*.md` 与 `libry.toml` 的 `content_dirs`（type=archive），解析 YAML frontmatter，join `index.md` 一行摘要与 `tags.md` 标准标签表，输出：

- `.libry/index.json` — 元数据（启动时整体载入内存；服务可现场重建）
- `.libry/content.json` — 全文纯文本语料（为未来 FTS/向量搜索备料，运行时不加载）

**链接解析**是全系统的地基：`[[X]]` 按归一化键（NFKC + 小写 + 去非字母数字，保留 CJK）匹配文件名 stem 或页面 H1，双注册、先注册者优先（wiki 页优先于顶层归档）。因此 `[[Vibe Coding]]` 能命中 `vibe-coding.md`。`tools/lint/` 与渲染器共用同一规则——lint 报的就是用户点击时真实发生的。

## 关联图（可选组件）

`pip install 'libry[graph]'` 后 `libry graph` 用 fastembed 本地算 embedding（BAAI/bge-small-zh-v1.5），与 wikilink/tag/source 结构信号加权合成 0~1 相关性，输出每文档 top-10 相关页与全图边表。graph.json 是派生数据：不入 git，构建后可经 SSH 直传对端；未安装或构建失败时 Web 端自动隐藏图功能（优雅降级）。

## 用户数据与多机同步

五个 JSON 文件（`.libry/` 下）：`users`（bcrypt 账户）、`state`（已读/新增水位）、`bookmarks`（收藏）、`visibility`（个人/共享覆盖层）、`deletions`（删除标记）。

单机部署下它们就是普通运行数据（gitignored）。启用多机同步时放开 gitignore 白名单，`libry sync-data` 经 vault 的 git 远端做双向合并：**CRDT 语义——按时间戳 LWW + 删除墓碑**，满足交换/结合/幂等律，无需三方 base、不会 git 冲突。

## 删除管道（标记-清理两段式）

1. Web 端垃圾桶（管理员）→ `deletions.json` 写 pending 标记。
2. `libry purge`（定时 ingest 前置步骤 / 设置页手动触发）：
   - 路径守卫（仅 wiki 四子目录 + content_dirs，防穿越）
   - 删文件 → 机械清理引用（wikilink→纯文本、index.md 摘行、frontmatter sources 移除）→ log.md 追加
   - 跨端防复活 reconcile：purged 终态 + 残留清理钩子（publish/sync-data 均内置）

## 定时与自动化

引擎不自带调度器——用系统原生机制（crontab / systemd timer / launchd，模板在 `deploy/cron/`）调用 `scripts/run-ingest.sh` / `run-lint.sh`。这两个脚本通过 `KB_AGENT_CMD`（如 `claude -p "{prompt}"`）无头驱动**任意** coding agent，按 vault 的 `AGENTS.md` 契约执行；结果经 `scripts/notify.sh` 推送（通用 webhook）。

## 技术决策速查

| 决策 | 理由 |
|---|---|
| 无 DB，纯 JSON 文件 + 线程锁 + 原子替换 | 单机个人/小团队规模下零运维；同步语义显式可控 |
| 前端无构建（vendored Vue/d3） | 升级引擎不碰 node 工具链；部署面最小 |
| git 作为多机传输层 | 无服务器依赖；vault 本来就要版本化 |
| 引擎与 vault 分离 | 引擎升级与内容历史解耦；vault 永远是「普通的 markdown 目录」 |
| Docker 延后到 v0.2 | 引擎链路深度依赖 git+ssh（publish/sync/purge），整体容器化复杂度高；裸机路径是当前主形态 |
