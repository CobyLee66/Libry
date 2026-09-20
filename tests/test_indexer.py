"""indexer 解析与构建。"""
import json

from libry.indexer import (
    build_index,
    normalize_key,
    parse_index_md,
    parse_tags_md,
    self_summary,
    split_frontmatter,
    to_date_str,
)


def test_split_frontmatter():
    meta, body = split_frontmatter("---\ntags: [a]\n---\n\n# Title\n正文\n")
    assert meta == {"tags": ["a"]}
    assert body.startswith("# Title")


def test_split_frontmatter_none():
    meta, body = split_frontmatter("# 只有正文")
    assert meta == {}
    assert body == "# 只有正文"


def test_normalize_key_equivalence():
    # 标题、kebab 文件名、去空格形式归一化后等价（引擎链接解析的根基）
    assert normalize_key("Vibe Coding") == normalize_key("vibe-coding")
    assert normalize_key("SSH 使用与隧道技术指南") == normalize_key("SSH使用与隧道技术指南")
    assert normalize_key("Don't Build Multi-Agents") == normalize_key("dont-build-multi-agents")


def test_to_date_str_quoted():
    assert to_date_str("2026-01-02") == "2026-01-02"


def test_parse_index_md(vault):
    summaries = parse_index_md(vault / "index.md")
    assert summaries[normalize_key("Foo Article")].startswith("一篇讲 foo")


def test_parse_tags_md(vault):
    standard, groups = parse_tags_md(vault / "tags.md")
    assert standard == ["测试"]
    assert "其它" in groups


def test_self_summary_substantive():
    body = "# 标题\n\n这一段是足够长的实质性正文段落，完全可以充当摘要来使用，超过长度门槛。\n"
    assert "实质性" in self_summary(body)


def test_self_summary_skips_meta():
    body = "# 标题\n\n作者：某人\n2026-01-01 12:00\n\n真正的正文段落是足够长的，可以被正常提取出来充当文档摘要。\n"
    assert "真正的正文" in self_summary(body)


def test_build_index(vault, env_clean):
    index, nonstandard = build_index(str(vault))
    files = {d["file"] for d in index["docs"]}
    assert files == {"wiki/sources/foo-article.md", "wiki/concepts/bar-concept.md",
                     "notes/note-1.md"}
    types = {d["file"]: d["type"] for d in index["docs"]}
    assert types["notes/note-1.md"] == "archive"
    docs = {d["file"]: d for d in index["docs"]}
    assert docs["wiki/sources/foo-article.md"]["summary"].startswith("一篇讲 foo")
    assert docs["wiki/concepts/bar-concept.md"]["summary"].startswith("bar")
    assert nonstandard == {}
    data = json.loads((vault / ".libry" / "index.json").read_text(encoding="utf-8"))
    assert data["doc_count"] == 3
    assert "notes/note-1.md" in json.loads(
        (vault / ".libry" / "content.json").read_text(encoding="utf-8"))
