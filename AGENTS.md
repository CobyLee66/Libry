# Libry（书阁）引擎 — Agent 开发手册

> 本文件是 **AI Agent 在本仓库（引擎）上干活时的操作契约**：开发规范、质量门、红线。
> 知识库 vault 侧的维护契约不在这里——那个由 `libry init` 生成的 vault 内 `AGENTS.md` 承担（模板见 `libry/templates/vault/AGENTS.md`）。

## 角色

你是 Libry 引擎的维护者：改代码、修 bug、加功能、写文档。**引擎是开源产品，一切改动以「任意用户可在自己的 vault 上使用」为标准。**

## 仓库结构

```
libry/                      Python 包（发布单元）
├── config.py               配置单一来源（libry.toml + env）——路径/目录清单只从这里来
├── __main__.py             CLI（所有子命令入口）
├── indexer.py              索引生成（wikilink 归一化的根基在此）
├── build_graph.py          关联图（可选依赖 fastembed，import 必须延迟到调用点）
├── purge_marked.py         标记-清理两段式执行端（机械引用清理）
├── sync_data.py            用户数据 CRDT 同步（合并函数保持纯函数、可单测）
├── server/                 FastAPI（auth/render/state/bookmarks/visibility/deletions/main）
├── static/                 Vue 3 前端（手写、无构建，风格规范见 docs/frontend-style.md）
└── templates/vault/        `libry init` 的脚手架源（AGENTS.md + agent-skills + 示例内容）
tools/lint/                 7 个独立可跑的结构检查脚本（`libry lint` 调用）
deploy/                     install/publish/sync/update + systemd/launchd/cron/Caddy 模板
scripts/                    定时入库/lint（KB_AGENT_CMD 抽象）+ notify
tests/                      pytest
docs/                       部署与接入文档
```

## 开发环境与质量门

```bash
python3.11 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/ruff check libry tests     # 必须 0 error
.venv/bin/pytest -q                  # 必须全过
shellcheck deploy/*.sh scripts/*.sh  # shell 改动时
```

**每次提交前三项全绿。** CI 跑同样内容外加「模板 vault 自检」：对 `libry/templates/vault` 跑 lint 必须零发现——改模板内容（含示例页、skills、AGENTS.md）后本地先跑：

```bash
.venv/bin/libry lint --root libry/templates/vault
```

## 代码规范

1. **无构建前端**：`libry/static/` 是手写 Vue 3（vendored）——不引入打包器/npm/CDN；UI 规范见 `docs/frontend-style.md`。
2. **纯函数优先**：`sync_data.py` 的合并函数、`purge_marked.py` 的清理函数保持纯函数形态（已有单测覆盖，改语义必须改测试）。
3. **配置单一来源**：新增路径/目录概念一律走 `config.py`，禁止在脚本里硬编码目录清单或绝对路径。
4. **可选依赖延迟导入**：fastembed/numpy 只在 `build_graph` 调用点 import（核心安装不含它们，缺失时优雅降级）。
5. **包内绝对导入**：server 模块用 `from ..indexer import …`，不用 sys.path hack。
6. **兼容性**：`libry/__main__.py` 的 CLI 子命令是公开接口，改名/去参数要在 CHANGELOG 标 breaking；`.libry/` 五个用户数据文件的 JSON 结构是跨端同步契约，改结构需要写迁移逻辑。
7. **注释与文档同改**：行为变更同步更新 docstring 与 `docs/`（API 改动更新 `docs/api.md`）。
8. **登录/凭据表单的密码管理器适配**（2026-09 于 MindTrace 项目本地二分实验实测）：登录表单须为页面加载时可见的唯一凭据 `<form>`；字段带 `name/id="username"|"password"` + `autocomplete="username"|"current-password"`；表单内只放提交按钮——多余 `type="button"` 按钮会致 LastPass 拒填密码（无文本 + 带 aria-label 的眼睛切换按钮可豁免）；注册/改密等隐藏区域用 `v-if` 不渲染（现状即如此）或散装 input，字段 `name` 不与登录表单重复。

## 发布流程

1. `CHANGELOG.md` 追加条目（格式契约见下节）；`libry/__init__.py` 与 `pyproject.toml` 的 version 同步 bump。
2. 质量门全绿 → commit → push → 打 tag `vX.Y.Z`。
3. `deploy/update.sh` 是用户侧升级入口——记得它假定可编辑安装（代码 pull 后重启即生效，依赖变更才重装）。

## 文档维护（README / CHANGELOG）

**README 双文件**：`README.md`（英文主）与 `README.zh-CN.md`（中文副）互为镜像，**必须同改同审**——结构、锚点、截图引用一一对应，内容漂移即缺陷。截图只放 `docs/images/readme-*.png`。

**CHANGELOG 维护规则**（GitHub 标准，Keep a Changelog + SemVer）：

1. **格式**：头部声明 + `## [Unreleased]` 常驻段 + 按版本倒序的 `## [X.Y.Z] - YYYY-MM-DD`；文件底部维护每个版本的 compare/tag 链接（`[Unreleased]: .../compare/vX.Y.Z...HEAD`）。
2. **类目**：只用标准类目 `Added` / `Changed` / `Fixed` / `Deprecated` / `Removed` / `Security`；破坏性变更在条目前缀 **BREAKING** 并在发版时确保 major/minor 语义正确。
3. **双语**：每条变更中英双语（英文一行 + 中文一行），只记「用户可见的为什么」，不复述实现细节。
4. **时机**：一切用户可见变更（功能、API 行为、CLI 接口、配置项）在提交前记入 `[Unreleased]`；发版时把该段改名为版本号 + 日期，并补底部链接。
5. **与代码同 PR**：CHANGELOG 更新和代码变更同一提交/PR，不事后补账。

## 敏感信息纪律（公开仓库）

本仓库是**公开仓库**——一旦公开，**全部 git 历史对全世界可见**，历史里也不得有敏感信息。任何本机/个人专属信息都不得入库：

- **禁止提交**：真实 vault 数据与用户数据、API key/token/密码/私钥、真实域名与公网/内网 IP、SSH 别名、个人绝对路径（`~/…`、`/Users/…`）、个人账户名、个人邮箱。
- 本机专属值一律走环境变量（`KB_*`）或 gitignored 配置文件；脚本默认值必须中性。
- 新增文档/脚本/测试夹具时自查：示例值一律用 `kb.example.com`、`/opt/libry`、`192.0.2.10`（TEST-NET-1）这类明显占位符。
- **截图纪律**：产品截图（`docs/images/`）只许拍 `libry init` 生成的演示 vault（模板示例内容为原创通用材料）；**绝不拍摄真实 vault**。开发调试截图只留本地、不入库。
- 测试夹具不得来自真实知识库内容；演示数据必须原创且通用。
- **提交前自查**：`git diff --cached | grep -inE "AI-Docs|/Users/|cobyli|@gmail|@qq\.com"`（关键词按自己环境补充，但别把真实值写进本文件）。

## 红线（违反即事故）

1. **绝不提交任何敏感信息**——细则见上节「敏感信息纪律」；本节是底线提醒：真实 vault 数据、用户数据、密钥、真实域名/IP/SSH 别名、个人路径、个人账户名。
2. **绝不引入对特定用户环境的依赖**：脚本里的路径全部经 env/config（`KB_ROOT`/`KB_*`），默认值必须中性（`kb.example.com`、`/opt/libry` 这类占位）。
3. **消毒管线不可拆**：`server/render.py` 的 `_sanitize`（nh3 白名单）是存储型 XSS 的唯一防线，改动需在 SECURITY.md 层面评估。
4. **模板内容保持原创与通用**：`templates/vault/` 的示例页、skills 不得携带真实知识库内容或版权材料。
