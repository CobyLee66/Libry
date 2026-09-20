#!/usr/bin/env python3
"""Libry 知识库索引生成器。

扫描 wiki/{sources,entities,concepts,synthesis}/*.md 与顶层内容目录
（libry.toml 的 content_dirs，type=archive 的原文/成品文章），解析 YAML
frontmatter，join index.md 的一句话摘要，解析 tags.md 的标准标签与分类
分组，输出：

- <data>/index.json   元数据索引（不含正文，服务启动时整体载入内存）
- <data>/content.json 全文纯文本语料（file → text，仅供未来 FTS5/向量
  搜索备料与 build_graph 的 embedding 哈希，运行时不加载）

只读 wiki/、content_dirs、index.md、tags.md，不修改任何知识库内容。
用法：libry index [--root VAULT] 或 python -m libry.indexer [vault_root]
"""
import json
import re
import sys
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from .config import WIKI_DIRS, get_config

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([^\[\]|]+)(?:\|([^\[\]]+))?\]\]")
INDEX_LINE_RE = re.compile(r"^-\s*\[\[([^\[\]]+)\]\]\s*—\s*(.+?)\s*$")
TAG_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|")
BOLD_TAG_RE = re.compile(r"\*\*([^*]+)\*\*")


def split_frontmatter(text: str):
    """返回 (frontmatter dict, body)。"""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    return meta, text[m.end():]


def to_date_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip().strip('"\'')


def extract_title(body: str, fallback: str) -> str:
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def body_to_plaintext(body: str) -> str:
    """去除 markdown 标记，保留纯文本语料（供未来 FTS5/向量搜索）。"""
    text = WIKILINK_RE.sub(lambda m: m.group(2) or m.group(1), body)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)          # 图片
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)      # 链接
    text = re.sub(r"[`*_#>~]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


SUMMARY_LEAD_RE = re.compile(r"^\*\*(简介|摘要|一句话|概述|导语|说明|核心结论)\*\*[：:]\s*(.+)$")
META_LINE_RE = re.compile(
    r"^(来源|作者|整理时间|整理日期|分析日期|数据截至|生成日期|更新时间|最后更新|更新日期|"
    r"发布时间|发布日期|固定网络参数|日期|标签|关键词)[：:]"
)
TIMECODE_RE = re.compile(r"^\d{1,2}:\d{2}(?::\d{2})?\s")
LABEL_VALUE_RE = re.compile(r"^[^：:]{2,8}[：:]\s*.{0,60}$")
URL_LINE_RE = re.compile(r"^https?://")
DATETIME_RE = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}")
MIN_SUMMARY_LEN = 25          # 正文段落门槛
MIN_QUOTE_LEN = 10            # 引言块门槛（人工写的引导句通常更短）

IMAGE_MD_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
LINK_MD_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def _clean_md(s: str) -> str:
    """去 markdown 噪声：整段图片丢弃、链接只留文字、去强调符。"""
    s = IMAGE_MD_RE.sub(" ", s)
    s = LINK_MD_RE.sub(r"\1", s)
    s = re.sub(r"[*`_]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _clip_summary(s: str, limit: int = 120) -> str:
    s = _clean_md(s)
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _is_substantive(text: str, min_len: int = MIN_SUMMARY_LEN) -> bool:
    """判断一段文字能否当摘要：排除元信息、清单项、时间码、URL 与未讲完的引导句。

    先在清洗后的文本上判断——这样「整段是图片」「链接/提及独占一行」会被正确判空。
    """
    text = _clean_md(text)
    if len(text) < min_len:
        return False
    if TIMECODE_RE.match(text) or URL_LINE_RE.match(text):
        return False
    # 短行里的「作者 + 时间戳」署名行
    if len(text) < 60 and DATETIME_RE.search(text):
        return False
    if text[0] in "-*+>|":
        return False
    if META_LINE_RE.match(text):
        return False
    if text.endswith(("：", ":")):
        return False
    # 形如「短标签：带数字的值」多为元信息（日期、参数清单）
    if LABEL_VALUE_RE.match(text) and any(c.isdigit() for c in text):
        return False
    return True


def self_summary(body: str, limit: int = 120) -> str:
    """归档原文（type=archive）无 index.md 摘要时，回退用文档自身的引言/首段。

    index.md 按规范只索引 wiki 页面（sources/entities/concepts/synthesis），
    顶层内容目录（content_dirs）的原文不会出现在其中——这里回退提取，
    避免 web 列表页对这些文档显示空摘要。无可提取时返回空串（宁缺毋滥，
    不把元信息/时间码当摘要）。纯只读派生，不改动知识库文件。
    """
    paragraphs = []
    blockquotes = []
    buf = []
    in_fence = False

    def flush():
        if buf:
            paragraphs.append(" ".join(buf))
            buf.clear()

    for raw in body.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not line or line.startswith(("#", "|")) or line == "---":
            flush()
            continue
        if line.startswith(">"):
            flush()
            text = line.lstrip(">").strip()
            if not text:
                continue
            m = SUMMARY_LEAD_RE.match(text)
            if m:
                return _clip_summary(m.group(2), limit)
            blockquotes.append(text)
            continue
        buf.append(line)
    flush()

    for para in paragraphs:
        if _is_substantive(para):
            return _clip_summary(para, limit)
    for bq in blockquotes:
        if _is_substantive(bq, MIN_QUOTE_LEN):
            return _clip_summary(bq, limit)
    return ""


def normalize_key(s: str) -> str:
    """归一化匹配键：NFKC + 小写 + 去除非字母数字字符（保留 CJK）。

    index.md 链接文本与中文文件名逐字一致，但英文页是 Title-Case 而文件名是
    小写 kebab-case、H1 标题又可能含撇号/空格，归一化后三者可互相命中。
    """
    return re.sub(r"[^\w一-鿿]+", "", unicodedata.normalize("NFKC", s).lower())


def parse_index_md(path: Path) -> dict:
    """index.md 每行 `- [[Title]] — 摘要`，返回 {归一化标题: 摘要}。"""
    summaries = {}
    if not path.exists():
        return summaries
    for line in path.read_text(encoding="utf-8").splitlines():
        m = INDEX_LINE_RE.match(line.strip())
        if m:
            summaries[normalize_key(m.group(1))] = m.group(2)
    return summaries


def parse_tags_md(path: Path):
    """返回 (standard_tags 集合, tag_groups {分类: [tag, ...]})。"""
    standard = []
    groups = {}
    if not path.exists():
        return standard, groups
    lines = path.read_text(encoding="utf-8").splitlines()

    in_table = False
    in_groups = False
    current_group = None
    for line in lines:
        if line.startswith("## "):
            in_table = "标准 Tag 全表" in line
            in_groups = "分类说明" in line
            current_group = None
            continue
        if in_table:
            m = TAG_ROW_RE.match(line)
            if m and m.group(1) not in ("Tag", "---"):
                tag = m.group(1).strip()
                if tag and not set(tag) <= {"-"}:
                    standard.append(tag)
            continue
        if in_groups:
            if line.startswith("### "):
                current_group = line[4:].strip()
                groups.setdefault(current_group, [])
                continue
            if current_group:
                for tag in BOLD_TAG_RE.findall(line):
                    for t in tag.split("/"):
                        t = t.strip().strip("`")
                        if t and t not in groups[current_group]:
                            groups[current_group].append(t)
    return standard, groups


def build_index(root=None):
    cfg = get_config(root)
    kb_root = cfg.kb_root
    data_dir = cfg.data_dir
    content_dirs = cfg.content_dirs
    summaries = parse_index_md(kb_root / "index.md")
    standard_tags, tag_groups = parse_tags_md(kb_root / "tags.md")
    standard_set = set(standard_tags)

    docs = []
    contents = {}  # file → 全文纯文本（存 content.json，主索引不再内嵌正文）
    nonstandard = {}  # tag -> 出现次数
    # (目录, type, 是否递归)
    scan_dirs = [(kb_root / "wiki" / dirname, dirname, False) for dirname in WIKI_DIRS]
    scan_dirs += [(kb_root / dirname, "archive", True) for dirname in content_dirs]
    for d, doc_type, recursive in scan_dirs:
        if not d.is_dir():
            continue
        paths = sorted(d.rglob("*.md")) if recursive else sorted(d.glob("*.md"))
        for path in paths:
            rel = path.relative_to(kb_root).as_posix()
            stem = path.stem
            text = path.read_text(encoding="utf-8")
            meta, body = split_frontmatter(text)
            tags = meta.get("tags") or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            tags = [str(t).strip() for t in tags if str(t).strip()]
            for t in tags:
                if t not in standard_set:
                    nonstandard[t] = nonstandard.get(t, 0) + 1
            sources = meta.get("sources") or []
            if isinstance(sources, str):
                sources = [sources]
            wikilinks = sorted({m.group(1).strip() for m in WIKILINK_RE.finditer(body)})
            title = extract_title(body, stem)
            summary = summaries.get(normalize_key(stem)) or summaries.get(normalize_key(title), "")
            if not summary and doc_type == "archive":
                summary = self_summary(body)
            # 个人/共享可见性：frontmatter 可选字段，缺省视为共享（存量文档零迁移）。
            # 此值是初始状态；web 端切换后以 data/visibility.json 覆盖层为准。
            visibility = str(meta.get("visibility") or "shared").strip().lower()
            if visibility not in ("shared", "personal"):
                visibility = "shared"
            doc = {
                "title": title,
                "file": rel,
                "type": doc_type,
                "tags": tags,
                "created": to_date_str(meta.get("created")),
                "updated": to_date_str(meta.get("updated")),
                "summary": summary,
                "sources": [str(s) for s in sources],
                "wikilinks": wikilinks,
                "visibility": visibility,
                "owner": str(meta.get("owner") or "").strip(),
            }
            contents[rel] = body_to_plaintext(body)
            docs.append(doc)

    index = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "doc_count": len(docs),
        "standard_tags": standard_tags,
        "tag_groups": tag_groups,
        "docs": docs,
    }
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    (data_dir / "content.json").write_text(
        json.dumps(contents, ensure_ascii=False), encoding="utf-8")
    return index, nonstandard


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else None
    index, nonstandard = build_index(root)
    cfg = get_config(root)
    print(f"索引已生成: {cfg.index_path}")
    print(f"条目数: {index['doc_count']}  标准标签: {len(index['standard_tags'])}  "
          f"分类分组: {len(index['tag_groups'])}")
    # index.md 按规范只索引 wiki 页面；归档原文（type=archive）的摘要由正文首段回退生成。
    wiki_missing = [d for d in index["docs"] if not d["summary"] and d["type"] != "archive"]
    if wiki_missing:
        print(f"摘要缺失（wiki 页面，需补 index.md）: {len(wiki_missing)}")
        for d in wiki_missing[:20]:
            print(f"  - {d['file']}")
    else:
        print("摘要缺失（wiki 页面）: 0")
    if nonstandard:
        total = sum(nonstandard.values())
        print(f"非标准 tag（未命中 tags.md 主表）: {len(nonstandard)} 种 / {total} 次")
        for tag, n in sorted(nonstandard.items(), key=lambda kv: -kv[1]):
            print(f"  - {tag} × {n}")
    else:
        print("非标准 tag: 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
