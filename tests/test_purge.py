"""purge 的路径守卫与引用清理（纯函数部分）。"""
from pathlib import Path

from libry.purge_marked import _allowed_rel, _clean_sources_block, clean_referencing_file, resolve_target


def test_resolve_target_guards(vault, env_clean):
    ok, err = resolve_target("wiki/sources/foo-article.md", vault)
    assert err == "" and ok == vault / "wiki" / "sources" / "foo-article.md"
    assert resolve_target("../etc/passwd", vault)[1]     # 越出
    assert resolve_target("wiki/log.md", vault)[1]        # 不在四个子目录
    assert resolve_target("other-dir/x.md", vault)[1]     # 不在 content_dirs
    assert resolve_target("notes/note-1.md", vault)[1] == ""   # content_dirs 内允许


def test_allowed_rel_content_dirs():
    assert _allowed_rel(Path("notes/a.md"), ["notes"])
    assert not _allowed_rel(Path("notes/a.md"), [])
    assert not _allowed_rel(Path("wiki/deep/a/b.md"))
    assert _allowed_rel(Path("wiki/sources/a.md"))


def test_clean_sources_block_inline():
    lines, removed = _clean_sources_block(
        ['tags: [a]', 'sources: [foo-article.md, "other.md"]', 'created: 2026-01-01'],
        "foo-article.md", "wiki/sources/foo-article.md")
    assert removed == 1
    assert "foo-article.md" not in lines[1]
    assert "other.md" in lines[1]


def test_clean_sources_block_list_style():
    lines, removed = _clean_sources_block(
        ['tags: [a]', 'sources:', '  - foo-article.md', '  - other.md', 'created: 2026-01-01'],
        "foo-article.md", "wiki/sources/foo-article.md")
    assert removed == 1
    joined = "\n".join(lines)
    assert "foo-article.md" not in joined
    assert "other.md" in joined


def test_clean_referencing_file_wikilink_and_index(vault, env_clean):
    targets = [("Foo Article", "foo-article", "foo-article.md", "wiki/sources/foo-article.md")]
    # 正文 wikilink → 纯文本
    page = vault / "wiki" / "concepts" / "bar-concept.md"
    n = clean_referencing_file(page, targets, kb_root=vault)
    assert n == 2  # 1 处正文 wikilink + frontmatter sources: 里的 1 条引用
    assert "[[Foo Article]]" not in page.read_text(encoding="utf-8")
    assert "Foo Article" in page.read_text(encoding="utf-8")
    # index.md 整行删除
    index = vault / "index.md"
    before = index.read_text(encoding="utf-8")
    n = clean_referencing_file(index, targets, kb_root=vault)
    assert n == 1
    after = index.read_text(encoding="utf-8")
    assert "[[Foo Article]]" not in after
    assert "Bar Concept" in after and len(after) < len(before)
