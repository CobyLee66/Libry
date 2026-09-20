# 贡献指南

欢迎 issue / PR。中文或英文均可。

## 开发环境

```bash
git clone https://github.com/CobyLee66/Libry.git && cd Libry
python3.11 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q          # 测试
.venv/bin/ruff check libry tests
shellcheck deploy/*.sh scripts/*.sh
```

提交前本地过一遍上面三项（CI 会跑同样的检查 + 模板 vault 自检）。

## 约定

- **无构建前端**：`libry/static/` 是手写 Vue 3（vendored）——新增 UI 遵循现有风格（Feather 线性图标、`.btn`/`.icon-btn`、`:root` CSS 变量、移动优先），不引入打包器/npm。
- **纯函数优先**：同步/合并/清理逻辑保持可单测的纯函数形态（见 `tests/test_sync_merge.py`）。
- **agent 契约改动**（`libry/templates/vault/AGENTS.md` 与 skills）要考虑向后兼容：用户 vault 里的副本不会自动更新（`libry skills update` 才同步），重大变更在 CHANGELOG 里醒目标注。
- lint 工具（`tools/lint/`）改动后必须对 `libry/templates/vault` 跑通（CI 有自检）。
- commit message 风格：`feat: …` / `fix: …` / `docs: …`。

## 目录速览

```
libry/            Python 包（server/ + indexer/build_graph/purge/sync_data + static/ + templates/vault）
tools/lint/       7 个独立可跑的结构检查脚本
deploy/           install.sh、publish/sync/update、systemd/launchd/cron/Caddy 模板
scripts/          定时入库/lint（KB_AGENT_CMD 抽象）与通用通知
tests/            pytest
docs/             部署与接入文档
```
