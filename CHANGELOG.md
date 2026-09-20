# Changelog

本项目遵循 [Semantic Versioning](https://semver.org/)。

## [0.2.0] - 2026-09-21

### 界面国际化（i18n）
- Web 端支持中英双语：`libry/static/i18n/`（手写轻量运行时，无新增依赖、无构建）。默认按浏览器语言自动检测（`zh*` → 中文，其余回退 English）；登录卡与设置页的语言下拉可手动切换（不占顶栏空间），持久化到 `localStorage['kb-lang']`
- 为后续语言打好基础：新增语言 = 加一个字典文件 + `index.html` 一行 `<script>` + `i18n/core.js` 的 `detect()` 一处映射；`t()` 支持 `{name}` 插值与 `{one, other}` 复数（`Intl.PluralRules`）
- 新增 `tests/test_i18n.py`：各语言 key 集合一致性、模板/JS 引用漏键、字典文件挂载检查

### API 行为变更（BREAKING）
- `HTTPException` 的 `detail` 由中文文案改为稳定错误码（snake_case，如 `invalid_credentials`），完整清单见 `docs/api.md`；脚本消费者请按错误码判断，不要解析自然语言文案
- `GET /api/deletions/status`（`.libry/purge-status.json`）：`ok` 结果新增结构化 `pages`（删除页数）/`refs`（清理引用数）字段，不再写自然语言 `detail`；`error` 的 `detail` 改存原始诊断输出（如 `publish.sh: <stderr>`），由前端原样透出

## [0.1.0] - 2026-09-20

首个公开版本。

### 引擎
- `libry init`：vault 脚手架（AGENTS.md 契约 + agent skills + 示例内容 + 随机密钥 + admin 密码 + git）
- `libry serve`：FastAPI + Vue 3 web 端（多账户、已读/新增、收藏夹、个人/共享可见性、删除标记）
- `libry index` / `graph` / `purge` / `sync-data` / `passwd` / `config` / `skills` / `lint` CLI
- 配置单一来源：vault 根 `libry.toml` + 环境变量（`KB_ROOT` / `KB_DATA_DIR` / `KB_ROLE` / `KB_GIT_BRANCH` / `KB_LOCAL_URL` / `KB_DEPLOY_KEY`）
- 关联图为可选组件（`pip install 'libry[graph]'`，fastembed 本地 embedding，缺失时优雅降级）
- 用户数据跨端同步：CRDT 风格 LWW + 删除墓碑，经 vault git 仓库双向合并

### Agent 工作流
- vault 模板自带 5 个 skills：kb-ingest / kb-lint / kb-publish / kb-query / kb-research-ingest（示例）
- `tools/lint/`：7 个结构检查脚本（wikilink/孤儿/索引/frontmatter/死链/sources/渲染），`libry lint` 一键跑
- `scripts/run-ingest.sh` / `run-lint.sh`：`KB_AGENT_CMD` 抽象驱动任意 coding agent 无头执行；`notify.sh` 通用 webhook 通知

### 部署
- `deploy/install.sh`：裸机安装（venv + systemd / launchd 自助安装）
- `deploy/publish.sh` / `sync.sh` / `update.sh` / `sync-data.sh`：多机同步链路（webhook + cron 双通道）
- systemd / launchd / crontab / Caddy 中性模板
