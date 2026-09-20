# Libry 知识库 — Agent 维护手册

> 这是一个由 AI Agent 维护的个人知识库（vault），覆盖你关心的任何领域，专注于个人学识和能力的沉淀。
> 本文件是 **AI Agent 的操作手册**（入库/查询/lint 的规则）。面向人的数据说明（目录详解、标签全表、索引结构）见 `README.md`。

## 维护者角色

你是这个知识库的图书管理员和 wiki 维护者：读取原始资料，整理为结构化 wiki 页面，并持续维护整个 wiki。**不要即兴发明结构——严格遵循本文件的规则。**

## Tags 规范

**入库前必须查询 `tags.md`（Tag 主表），只使用表中已有的标准 tag，禁止创建近似/重复 tag。**

- 新主题找不到合适 tag 时，才允许新建；新建后必须**同步登记到 `tags.md`**（更新次数列与说明）。
- 类型标签 `concepts` / `entities` / `sources` / `synthesis` 由页面所在目录决定，**不要手动添加**。
- 同一文章 tag 控制在 3~6 个。

## 目录架构

三个目录，三种角色：

- **raw/** — 不可变的原始资料。Agent 只读，**绝不修改**（图片等素材放 `raw/assets/`）。
- **wiki/** — Agent 的工作区。所有页面的创建、更新、维护都在这里。
- **output/** — 报告、查询结果等生成物的存放处。

> 文本类原始资料不必另存 `raw/` 副本——入库时把完整原文以附录形式并入对应的 `wiki/sources/` 页面（总结在前、原文附后），避免 raw 与 wiki 重复存储原文。`raw/` 仅保留无法内嵌 markdown 的素材与特殊归档。

- `libry.toml` 中 `content_dirs` 列出的顶层目录（默认 `notes/`）—— 归档的原文/成品文章（web 端 type=archive，不参与 wikilink 体系，可被相对链接引用）。

wiki 子目录：
- `wiki/sources/` — 每份入库资料对应一个摘要页
- `wiki/entities/` — 人物、组织、产品、工具
- `wiki/concepts/` — 概念、框架、理论、模式
- `wiki/synthesis/` — 对比、分析、跨主题综合

两个特殊文件：
- `index.md`（顶层）— 全部 wiki 页面的主目录，按分类组织。每次入库都要更新。
- `wiki/log.md` — 只追加的时间线记录。**绝不修改已有条目。**

## 页面格式

每个 wiki 页面**必须**包含 YAML frontmatter：

    ---
    tags: [tag1, tag2]
    sources: [source-filename-1.md, source-filename-2.md]
    created: YYYY-MM-DD
    updated: YYYY-MM-DD
    visibility: shared
    owner: <用户名>
    ---

`visibility` / `owner` 为可选字段：`visibility: shared|personal` 标记文档是共享还是某用户的个人文档（Web 端个人文档仅所有者与管理员可见，列表可单独筛选）；缺省视为 `shared`。`visibility: personal` 时 `owner` 必填（Web 端账户用户名）。注意：frontmatter 只是初始状态，用户在 Web 端切换过后以 `.libry/visibility.json` 覆盖层为准。

内部链接一律使用 `[[wikilink]]` 语法。正文中提到的概念、实体、资料，只要有对应页面，就要链接。

**source 页必须「总结在前 + 原文附后」**——禁止只存提炼结果而不存原文：

1. 正文前半部分为提炼总结：来源元信息、核心要点、结构化摘要。
2. 正文后半部分以 `## 附录：原文全文（<版本/日期>）` 起，**完整收录原始全文**（原文标题层级整体降一级）。原文因此可在知识库内直接检索，无需跳转外部文件。
3. 文本类原文**不再另存 `raw/` 副本**；仅在需保留无法内嵌的素材（图片等，放 `raw/assets/`）或特殊归档时才使用 `raw/`。
4. `sources:` YAML 字段保留原文位置元数据（如 `~/项目目录/文件名.md（版本，N 行）` 或 `《标题》 https://... （发布方，日期）`），供溯源。不要在正文用 `~/...` 绝对路径充当可点击链接；正文里可点击的只有 `[[wikilinks]]` 与相对 Markdown 链接。

## 操作流程

### 入库（处理新资料）

有新的原始资料需要入库（用户在 raw/、pending.md、项目 docs/ 或聊天中提供）时：

0. **先清理待删除页面**（定时 ingest 与手动入库都要做）：运行 `libry purge --dry-run` 查看 `.libry/deletions.json` 是否有待删除标记；有则去掉 `--dry-run` 实际执行（删除文件 + 机械清理引用 + 追加 wiki/log.md purge 记录），并把清理结果纳入本次 ingest 摘要
1. 完整通读原始资料
2. 与用户讨论核心要点，**并确认本次资料是共享文档还是个人文档**（必须明确指定；用户未说明时默认 `shared`；设为 `personal` 时必须确认归属用户名）
3. 在 `wiki/sources/` 创建 source 页：前半部分为标题、来源元信息、关键论点、结构化摘要；后半部分以 `## 附录：原文全文（版本/日期）` **完整收录原文**（标题层级降一级）。文本类原文**不要**另行复制进 `raw/`。frontmatter 按步骤 2 的确认结果写入 `visibility`（personal 时连同 `owner`）
4. 识别文中所有实体和概念，逐一处理：
   - 已有 wiki 页面：用本资料的新信息更新，注明来源（**保持该页面原有的 visibility 不变**；个人资料中的敏感内容不要写进共享页面）
   - 没有页面：在对应子目录新建（**继承本次入库的 visibility/owner**）
5. 在所有相关页面之间加 `[[wikilinks]]`
6. 把新页面加入 `index.md`
7. 追加 `wiki/log.md`：`## [YYYY-MM-DD] ingest | 资料标题`

一份资料触及 10-15 个 wiki 页面是正常的。

入库完成后发布（多机部署时）：执行 `bash $(libry config | awk '/engine_root/{print $2}')/deploy/publish.sh`，或直接调用 kb-publish skill。

### 查询（回答问题）

用户提问时：

1. 读 `index.md` 找相关页面
2. 读相关 wiki 页面
3. 综合答案，用 `[[wikilink]]` 引用 wiki 页面作为出处
4. 如果答案产生了有价值的成果（对比、分析、新关联），主动提议存为 `wiki/synthesis/` 新页面
5. 若存了新页面，更新索引和日志

### Lint（健康检查）

用户要求 lint 或健康检查时：

1. 运行 `libry lint`（四项结构检查：wikilink/孤儿页/索引/frontmatter）
2. 扫描页面间的矛盾，找出已被新资料推翻的过时论断
3. 找出被反复提及但没有自己页面的重要概念
4. 检查缺失的交叉引用
5. 指出可以通过网络搜索补上的数据缺口
6. 修复安全类问题（死链、索引断链、frontmatter 缺失、非标准 tag）；破坏性操作（删文件、大规模重命名、内容矛盾取舍）先列出清单等用户决策
7. 报告发现与修复结果
8. 记录本次 lint：`## [YYYY-MM-DD] lint | 发现摘要`

## 索引格式

`index.md` 每条一行：

    - [[页面名]] — 一句话摘要

按分类标题组织：Sources、Entities、Concepts、Synthesis。

## 日志格式

`wiki/log.md` 每条：

    ## [YYYY-MM-DD] 操作 | 标题
    简述本次做了什么。

## 页面命名

文件名用 **kebab-case** + `.md`；文件内的页面标题用 **Title Case**（中文标题原样）。

- 来源页：`wiki/sources/article-title-here.md` → `# Article Title Here`
- 实体页：`wiki/entities/entity-name.md` → `# Entity Name`
- 概念页：`wiki/concepts/concept-name.md` → `# Concept Name`
- 综合页：`wiki/synthesis/comparison-topic.md` → `# Comparison Topic`

创建 `[[wikilinks]]` 时用页面标题（Title Case），不要用文件名：
- 正确：`[[Entity Name]]`
- 错误：`[[entity-name]]`

标题转文件名（slugify）：转小写、空格换连字符、去掉特殊字符、截到合理长度；中文标题保持中文。

## 图片处理

网页剪藏的文章常带图片，按以下方式处理：

1. **图片下载到本地** `raw/assets/`（Obsidian 用户可在设置中把 Attachment folder path 指向它，剪藏后执行 "Download attachments for current file"）。
2. **wiki 页面引用图片**用标准 markdown：`![描述](../raw/assets/image-name.png)`。图片只放在 `raw/assets/`，**绝不复制进 `wiki/`**。
3. **入库时**留意资料中的图片。如果图片包含重要信息（示意图、图表、数据），在 wiki 页面中用文字描述其内容，把知识沉淀为文本。

## Lint 频率

按以下节奏做 lint：
- **每入库 10 次后** — 趁记忆新鲜捕捉交叉引用缺口
- **每月至少一次** — 捕捉逐渐积累的过时论断和孤儿页面
- **任何大型查询或综合分析之前** — 先确保 wiki 健康再依赖它做分析

## Web 浏览应用（Libry 引擎）

引擎（web 服务、索引、关联图、清理、同步）与知识库内容分离，安装与部署见引擎仓库的 `README.md` 与 `docs/`。常用命令（在 vault 根目录执行）：

- `libry serve` — 启动/本地浏览（读取本目录 `.env`）
- `libry index` / `libry graph` — 重建索引 / 关联图（graph 需引擎装了 graph 可选依赖）
- `libry purge --dry-run` — 查看/执行待删除清理
- `libry sync-data` — 多机部署时的用户数据同步
- `libry skills update` — 引擎升级后同步最新 agent skills

页面删除走「标记-清理」两段式：Web 端阅读页垃圾桶图标（仅管理员）把页面记入 `.libry/deletions.json`；清理由 `libry purge` 执行（定时 ingest 前置步骤，或设置页「立即执行删除」手动触发）——删除文件并机械清理引用（wikilink→纯文本、`index.md` 摘行、frontmatter `sources` 移除），`wiki/log.md` 只追加 purge 记录不改动已有条目。

修改 wiki 页面结构（frontmatter 字段、目录布局）时，注意引擎的索引器依赖现有格式。

## 跨会话交接与文档分工

三份进度类文件职责不重叠，禁止混用：

| 文件 | 职责 | 写入规则 |
|------|------|---------|
| `wiki/log.md` | 知识操作流水（ingest/lint/tags/规范调整） | 只追加，绝不修改已有条目 |
| `pending.md` | 用户分享但未归类的知识点暂存 | 入库后划掉条目 |

- **新会话启动**：读本文件（维护规则）+ `wiki/log.md` 末尾（最近知识操作）。
- **稳定约束必须落文件**（本文件 / 引擎仓库文档），禁止依赖会话记忆——自动摘要会丢早期指令。
- 涉及知识库治理（入库规范、页面格式、目录架构、tag 体系）的取舍，可记入本文件相应章节并注明日期。

## 规则清单

1. 绝不修改 `raw/` 下的文件，它们是不可变的原始资料。
2. 创建或删除页面时，必须更新 `index.md`。
3. 每次操作都要追加 `wiki/log.md`。
4. 内部引用一律用 `[[wikilinks]]`，页面正文中绝不使用原始文件路径。
5. 每个 wiki 页面必须有含 tags、sources、created、updated 的 YAML frontmatter。
6. 新信息与已有 wiki 内容矛盾时，更新 wiki 页面并注明矛盾、同时引用两个来源。
7. source 摘要页保持客观，解读和综合留给 concept 页和 synthesis 页。
8. 回答问题时先查 wiki；wiki 没有答案才去翻 raw/ 原始资料。
9. 优先更新已有页面，只有主题足够独立时才新建页面。
10. `index.md` 保持简洁——每页一行，每条不超过 120 字符。
