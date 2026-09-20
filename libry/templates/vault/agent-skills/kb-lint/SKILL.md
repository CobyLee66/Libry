---
name: kb-lint
description: >
  知识库健康检查与修复。用户说「lint」「健康检查」「检查一下知识库」，
  或定时任务到点时使用；发现问题时默认自动修复安全类问题。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# kb-lint — 知识库健康检查与修复

检查并**修复**（不只是报告）知识库的结构问题。规则权威是 `AGENTS.md` 的 Lint 章节。

## 执行顺序

```bash
libry lint          # 一次跑四项结构检查（wikilink/孤儿/索引/frontmatter + 死链/sources/YAML）
```

需要单项细查或引擎是 git clone 安装时，也可直接调引擎的工具脚本（路径见 `libry config` 的 engine_root）：

```bash
ENGINE=$(libry config | awk '/engine_root/{print $2}')
python3 "$ENGINE/tools/lint/lint_wiki.py"            # 主检查：wikilink/孤儿/索引/frontmatter/untitled H1
python3 "$ENGINE/tools/lint/check_dead_links.py"     # 扩展：正文死链/sources 可达性/YAML 解析/双 frontmatter
python3 "$ENGINE/tools/lint/check_index_strict.py"   # index 严格比对
python3 "$ENGINE/tools/lint/verify_links.py"         # 全库链接复核（改名/去重后必跑）
```

脚本均接受 vault 根目录作第一参数（默认取 `KB_ROOT` 环境变量或当前目录）。

## 修复策略（默认自动修复）

- **直接修（安全类）**：正文死链、索引断链/重复、frontmatter 缺失或 YAML 引号错误、`sources:` 不可达引用、untitled H1、tags 非标准但可唯一映射到主表、孤儿页因索引修复自动消除。修完重跑 `libry lint` 验证归零。
- **停下来报告、等用户决策（破坏性/歧义类）**：删除文件、大规模重命名、内容矛盾取舍、新建 10+ 页、无法唯一映射的 tag 新建登记、往旧页回填大段原文附录。

## 语义检查（脚本之外，逐项人工判断）

1. 页面间的矛盾；已被新资料推翻的过时论断（更新页面并双源注明）
2. 被反复提及但没有自己页面的重要概念（建议建页）
3. 缺失的交叉引用（该链接而没链接的提及）
4. 可通过网络搜索补上的数据缺口（列出，交用户决定是否补）

## 已知坑（修复时务必遵守）

1. **死链正则不要用 `[^)\s]+`**——文件名含空格会整条漏掉；用 `[^)\n]+` 再去 `<>`，用 `os.path.exists` 判定。
2. **扫描范围**：只扫 wiki/ 四子目录 + `libry.toml` 的 content_dirs；引擎目录、`raw/`、`output/` 不扫（假孤儿）。
3. **代码块与行内代码里的 `[[...]]` 不是链接**——先剥离 fence/反引号再扫描。
4. **标题含 `|` 的 wikilink 已转义**（`\|`）——解析时按字面管道处理，不要当 alias 分隔符切。
5. **index.md 行删除必须先于 wikilink 替换**（wikilink 替换会把 `[[...]]` 剥掉，之后匹配不到整行）。
6. **frontmatter 重写脚本要幂等且整行替换**：`re.sub(r"^sources:.*$", new, fm, count=1, flags=re.M)`；用位置切片拼 `sources:` 键会产生 `sources: sources:` 双写，曾一次损坏数百文件。
7. **重复 frontmatter 检测**用文件头正则 `^---\n.*?\n---\n\n+---\n`，不要 `grep -c '^---$'`（水平分割线假阳性）；合并规则：tags/sources/aliases 取并集、created 取最早、updated 取最晚；写盘前断言第二段之后的正文逐字不变。
8. **`created: "2026-05-01"`（带引号日期）不是缺失**——先查引号变体再报缺失。
9. **macOS APFS 大小写不敏感**：`git rm`/`mv` 一个与目标仅大小写不同的路径会静默删掉新文件；比较 git 索引与磁盘时用 `git ls-files -z`（CJK/空格路径默认带引号）。
10. **wikilink 归一化**与引擎一致：NFKC + 小写 + 去所有非字母数字（保留 CJK）；标题与 kebab 文件名双向注册，先注册者优先（wiki/ 页优先于顶层 archive 文档）。

## 收尾（每次 lint 之后）

1. `wiki/log.md` 追加 `## [YYYY-MM-DD] lint | 发现与修复摘要`（含前后数字对比）
2. 多机部署时：git commit + push，再执行 `kb-publish` skill 通知对端
3. 无人值守（cron）场景：把结论写报告文件并经 `scripts/notify.sh` 推送（见 `KB_AGENT_CMD`/`LIBRY_NOTIFY_WEBHOOK` 配置）
