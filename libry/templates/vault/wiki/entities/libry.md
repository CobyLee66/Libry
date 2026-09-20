---
tags: [工具, 知识库管理]
sources: ["原创整理：Libry 项目自述"]
created: 2026-01-01
updated: 2026-01-01
---

# Libry

**Libry**（书阁）是维护本知识库的开源引擎：一个可部署在本地或服务器上的个人知识库系统，由 AI Agent 负责入库与健康检查，人通过 Web 界面阅读。

## 核心构成

- **引擎与内容分离**：引擎是 Python 包（web 服务 + 索引/关联图/清理/同步工具），知识库（vault）是纯 markdown 目录——永远可以直接用任意编辑器打开，不锁数据。
- **Agent 契约**：vault 根的 `AGENTS.md` 定义入库/查询/lint 规则，`.agents/skills/` 提供 kb-ingest、kb-lint、kb-publish 等技能；任何支持该约定的 coding agent 都能承担图书管理员角色。
- **阅读端**：FastAPI + Vue 3（无构建步骤），多账户、已读/新增状态、收藏夹、文档级个人/共享可见性、embedding 关联图（可选组件）。
- **多机同步（可选）**：vault 本身是 git 仓库，内容经 git 同步；用户数据（已读/收藏/账户）用 CRDT 式 LWW+墓碑语义经同一仓库双向合并。

## 相关概念

- [[Second Brain]] — Libry 是 Second Brain 理念的一种工程化实现
- [[Zettelkasten]] — wiki 子目录与 `[[wikilink]]` 体系借鉴了卡片盒的原子化+链接思想
