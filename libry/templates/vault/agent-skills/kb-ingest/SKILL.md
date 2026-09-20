---
name: kb-ingest
description: >
  把原始资料入库为结构化 wiki 页面。当用户添加了资料并说「入库」「处理这篇资料」
  「process this source」「ingest」，或定时任务需要检查待入库内容时使用。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# kb-ingest — 知识库入库

把原始资料整理为互相链接的 wiki 页面。**规则最高权威是 vault 根的 `AGENTS.md`——每次入库前重读一遍。**

## 找出待处理资料

1. 用户明确指定了文件/链接 → 用那些
2. 用户说「处理新资料」之类 → 检测未处理内容：
   - `pending.md` 里未划掉的条目
   - `raw/` 下的新文件（排除 `raw/assets/`）
   - 读 `wiki/log.md`，凡 ingest 条目已记录过的来源即为已处理
3. 没有待处理内容 → 告诉用户并结束

## 每份资料的处理流程

### 0. 前置：清理待删除页面

```bash
libry purge --dry-run     # 有待删除标记则去掉 --dry-run 实际执行
```

结果纳入本次 ingest 摘要。

### 1. 完整通读

读全文；图片含重要信息（示意图/图表/数据）时单独读图，把知识用文字沉淀进页面。

### 2. 与用户确认要点（交互式入库时）

分享 3~5 个核心要点，询问是否要侧重或跳过某些主题；**并确认共享/个人归属**（用户不提默认 `shared`；仅当内容含 PII/敏感信息时建议 `personal` 并确认归属用户名）。定时/无人值守入库跳过讨论，按默认规则执行并在报告中注明。

### 3. 创建 source 页（总结在前 + 原文附后）

`wiki/sources/<slug>.md`：

```markdown
---
tags: [从 tags.md 主表选 3~6 个]
sources: [原文位置元数据，如 "《标题》 https://... （发布方，日期）"]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# 来源标题

**来源**：…  **入库日期**：…  **类型**：文章 | 论文 | 字幕 | 笔记

## 核心要点 / 结构化摘要

## 附录：原文全文（<版本/日期>）

（完整原文，标题层级整体降一级）
```

文本类原文**不另存 raw/ 副本**；仅图片等无法内嵌的素材放 `raw/assets/`。

### 4. 更新实体与概念页

对文中每个人物/组织/产品/工具（entity）与概念/框架/理论/模式（concept）：

- 已有页面：追加新信息、`sources:` 加来源、更新 `updated:`；**保持该页原有 visibility 不变**；个人资料中的敏感内容不写进共享页面；与已有内容矛盾时注明矛盾并双源引用
- 没有页面：在 `wiki/entities/` 或 `wiki/concepts/` 新建（继承本次入库的 visibility/owner）

### 5. 补 wikilinks

所有相关页面之间用 `[[wikilink]]` 互链（用页面标题，不用文件名）。写新页前先核对要链接页面的确切 `# H1`，避免自造断链。

### 6. 更新 index.md

新页面加入对应分类（Sources/Entities/Concepts/Synthesis）标题之下——**不要追加到文件末尾**：

```markdown
- [[页面名]] — 一句话摘要（≤120 字符）
```

### 7. 追加 wiki/log.md

```markdown
## [YYYY-MM-DD] ingest | 资料标题
处理 <来源>。新建 N 页、更新 M 页。新实体：[[…]]。新概念：[[…]]。
```

### 8. 收尾

- 入库后跑 `libry lint` 验证结构归零（wikilink 断链/孤儿页/索引断链/frontmatter）
- 多机部署时执行 `kb-publish` skill 发布同步
- 向用户报告：新建/更新了哪些页、新实体新概念、发现的矛盾

## 惯例

- source 页**只做客观陈述**，解读和综合留给 concept/synthesis 页
- 一份资料触及 10~15 个 wiki 页面是正常的
- 优先更新已有页面，主题足够独立才新建
- tags 必查 `tags.md` 主表；新 tag 先登记再使用
- 引擎的链接归一化规则：标题与 kebab 文件名经 normalize（NFKC+小写+去非字母数字）等价，写入时保持页面内风格一致即可，不要批量改存量链接
