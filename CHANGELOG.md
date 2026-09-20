# Changelog

本项目遵循 [Semantic Versioning](https://semver.org/)。

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
