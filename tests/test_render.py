"""渲染管线回归测试：raw/ 文本链接降级、图片语法保留（素材由 /raw/assets 路由服务）。"""
from pathlib import Path

from libry.server.render import build_link_map, render_document


def _make_doc(tmp_path: Path, body: str) -> Path:
    kb_root = tmp_path
    md = kb_root / "wiki" / "concepts" / "demo.md"
    md.parent.mkdir(parents=True)
    md.write_text(body, encoding="utf-8")
    return md


def test_markdown_image_to_raw_assets_is_preserved(tmp_path):
    """![alt](../raw/assets/x.png) 必须保留 img 标签：站内素材走 /raw/assets 路由显示。"""
    md = _make_doc(tmp_path, "# 标题\n\n![测试图](../raw/assets/test.png)\n")
    html = render_document(md, {}, tmp_path, set())
    assert '<img alt="测试图" src="../raw/assets/test.png">' in html


def test_markdown_link_to_raw_is_downgraded(tmp_path):
    """普通链接指向 raw/ 文本源仍降级为纯文本（raw 文本不对外暴露）。"""
    md = _make_doc(tmp_path, "# 标题\n\n[本地存档](../raw/source.txt)\n")
    html = render_document(md, {}, tmp_path, set())
    assert "raw" not in html
    assert "本地存档" in html


def test_wikilink_still_converted_after_lookbehind_fix(tmp_path):
    """图片负向断言不得影响 wikilink 与普通站内链接的改写。"""
    docs = [{"file": "wiki/sources/foo.md", "title": "Foo", "tags": []}]
    link_map = build_link_map(docs)
    md = _make_doc(tmp_path, "# 标题\n\n见 [[Foo]] 与 [外部](https://example.com)。\n")
    html = render_document(md, link_map, tmp_path, {"wiki/sources/foo.md"})
    assert 'href="#/doc/wiki/sources/foo.md"' in html  # quote() 默认保留斜杠（现有行为）
    assert 'href="https://example.com"' in html
