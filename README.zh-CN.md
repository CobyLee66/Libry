[English](README.md) · **简体中文**

# Libry（书阁）

**AI Agent 维护的个人知识库** —— 你负责阅读与决策，agent 负责入库、整理与健康检查。

Libry 是一个开源、可部署在本地或服务器上的 second-brain 系统：

- **引擎与内容分离**：知识库（vault）是纯 markdown 目录（Obsidian 兼容），永远不锁数据；引擎是一个轻量 Python 包（FastAPI + Vue 3，无前端构建步骤）。
- **Agent 承担图书管理员**：vault 自带 `AGENTS.md` 契约与 `.agents/skills/`（kb-ingest / kb-lint / kb-publish / kb-query），任何 coding agent（Claude Code、hermes、ZCode、Codex……）读到即可上岗；定时任务让入库与 lint 全自动跑。
- **为阅读而生**：多账户、已读/新增跟踪、阅读进度记忆（「继续阅读」卡片）、收藏夹与位置书签、文档级个人/共享可见性、基于 embedding 的关联图（可选组件）、双端 git 同步。
- **部署极简**：`libry init` 一条命令脚手架；`deploy/install.sh` 裸机装服务（systemd / launchd + Caddy 模板）。Docker 支持在路线图上（v0.2+）。

<p align="center">
  <a href="#界面速览"><img src="docs/images/readme-library.png" width="280" alt="文库：文档列表、已读/新增跟踪与标签" /></a>
  &nbsp;&nbsp;
  <a href="#界面速览"><img src="docs/images/readme-reader.png" width="280" alt="阅读页：wikilink 渲染、标签与元信息" /></a>
  &nbsp;&nbsp;
  <a href="#界面速览"><img src="docs/images/readme-graph.png" width="280" alt="关联图：基于 embedding 的点状关联，节点按类型着色" /></a>
</p>

---

## 快速开始

**要求**：Python 3.11+、git。

```bash
# 1. 安装引擎
git clone https://github.com/CobyLee66/Libry.git ~/Libry
cd ~/Libry && python3.11 -m venv .venv && .venv/bin/pip install .

# 2. 创建你的知识库（交互式设置 admin 密码；--no-git 跳过 git 初始化）
.venv/bin/libry init ~/my-kb --title "我的知识库"

# 3. 启动
cd ~/my-kb && ~/Libry/.venv/bin/libry serve
# → http://127.0.0.1:8000
```

让 AI agent 开始维护（在 vault 目录下打开你的 coding agent，或直接把资料给它）：

```bash
cd ~/my-kb
claude "按 AGENTS.md 把这篇文章入库：https://example.com/article"
```

部署到服务器 / 开机自启 / 关联图 / 多机同步：见下方文档链接。

---

## 界面速览

截图均拍自 `libry init` 生成的**演示 vault**——内容为原创示例，绝不拍摄真实知识库。

| | |
|:---:|:---:|
| **文库** —— 文档列表、已读/新增跟踪、标签徽章、标题/摘要搜索与可见性切换；界面自动跟随浏览器语言（中文 / English） | **阅读页** —— wikilink 内联渲染、标签与日期元信息、反向链接；底层就是纯 markdown |
| <img src="docs/images/readme-library.png" width="420" alt="文库视图" /> | <img src="docs/images/readme-reader.png" width="420" alt="阅读页视图" /> |
| **关联图** —— 每个页面一个节点，按类型着色（sources / entities / concepts / synthesis）；边由 wikilink、tag、source 结构信号与本地 embedding（`libry graph`，可选组件）加权合成 0~1 相关度——支持缩放、拖拽、按类型/tag 过滤，点节点直达页面 | **登录** —— 多账户 + 文档级个人/共享可见性；个人文档对无权者与 404 不可区分 |
| <img src="docs/images/readme-graph.png" width="420" alt="关联图视图" /> | <img src="docs/images/readme-login.png" width="420" alt="登录视图" /> |

---

## 它如何工作

```
┌─────────────────────── vault（你的知识库，纯 markdown + git）───────────────────────┐
│  AGENTS.md（agent 契约）   .agents/skills/（kb-ingest/lint/publish/query）            │
│  wiki/{sources,entities,concepts,synthesis}/   index.md   tags.md   wiki/log.md      │
│  content_dirs（notes/…，归档原文）   raw/assets/（图片）   .libry/（运行数据）        │
└───────────────▲───────────────────────────────────────────────▲─────────────────────┘
                │ 读写                                          │ git 同步（可选多机）
┌───────────────┴──────────────┐                    ┌───────────┴──────────┐
│  Libry 引擎（本仓库）         │                    │  另一端（VPS/笔记本） │
│  libry serve  FastAPI+Vue    │◀── webhook/cron ──▶│  只读消费 + 数据合并  │
│  libry index/graph/purge     │                    │  CRDT LWW+墓碑同步   │
│  libry lint（tools/lint×7）  │                    └──────────────────────┘
└──────────────────────────────┘
         ▲
         │ KB_AGENT_CMD（任意 coding agent 无头调用）
  定时入库/定时 lint/通知（scripts/）
```

- **入库**：agent 按 `AGENTS.md` 流程产出 source 页（总结在前 + 原文附后）、更新实体/概念页、维护 index/tags/log，然后 `kb-publish` 发布。
- **健康检查**：`libry lint` 跑 7 个结构检查（wikilink 断链、孤儿页、索引一致性、frontmatter、死链、sources 可达性、渲染管线）。
- **删除**：Web 端标记 → `libry purge` 机械清理（删文件、wikilink 转纯文本、index 摘行、log 追加），跨端防复活。

---

## CLI 一览

```
libry init [PATH]        脚手架 vault（模板 + 随机密钥 .env + admin 密码 + git）
libry serve              启动 Web 服务（读 vault .env）
libry index / graph      重建索引 / 关联图（graph 需 pip install 'libry[graph]'）
libry lint               结构健康检查（7 项）
libry purge [--dry-run]  执行待删除清理（标记-清理两段式的执行端）
libry sync-data          多机用户数据同步（CRDT 合并）
libry passwd [USER]      设置/修改账户密码
libry skills update      引擎升级后同步最新 agent skills 进 vault
libry config             打印解析后的配置（engine_root / kb_root / content_dirs）
```

配置：vault 根 `libry.toml`（title、content_dirs）+ 环境变量（`KB_ROOT`、`KB_DATA_DIR`、`KB_ROLE`、`KB_GIT_BRANCH`、`KB_LOCAL_URL`、`KB_DEPLOY_KEY` 等，详见各脚本头注释与 docs/）。

---

## 文档

| 主题 | 文件 |
|---|---|
| 架构与数据流 | [docs/architecture.md](docs/architecture.md) |
| 裸机部署（Ubuntu VPS 从零 / macOS） | [docs/deploy-bare.md](docs/deploy-bare.md) |
| Agent 接入（任意 coding agent + 定时任务） | [docs/agent-integration.md](docs/agent-integration.md) |
| 多机同步（Mac + VPS 双端） | [docs/multi-node-sync.md](docs/multi-node-sync.md) |
| 知识库维护规则（agent 契约全文） | vault 内 `AGENTS.md`（`libry init` 生成） |
| 引擎开发规范（本仓库贡献者/agent 必读） | [AGENTS.md](AGENTS.md) |
| 前端风格规范 | [docs/frontend-style.md](docs/frontend-style.md) |
| API 一览 | [docs/api.md](docs/api.md) |

---

## 安全模型

- 会话：itsdangerous 签名 cookie（7 天）+ bcrypt 密码哈希；登录/同步端点限速。
- 渲染：nh3 白名单消毒（存储型 XSS 防线）+ Caddy CSP 模板。
- 个人文档：仅所有者与管理员可见，对无权者与 404 不可区分。
- 密钥全部在 vault 根 `.env`（gitignored，`libry init` 随机生成）。
- 报告漏洞：[SECURITY.md](SECURITY.md)。

## 路线图

- [ ] v0.2：Docker（仅 web 读取端容器化，git/agent 工具链留宿主机）
- [ ] v0.2+：FTS5 全文搜索（content.json 已备料）、PyPI 发布
- [ ] 欢迎提 issue / PR：[CONTRIBUTING.md](CONTRIBUTING.md)

## License

[MIT](LICENSE) © 2026 CobyLee66
