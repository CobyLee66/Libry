"""Markdown → HTML 服务端渲染。

- 剥离 YAML frontmatter
- [[wikilink]] / [[wikilink|别名]] → 站内路由链接 #/doc/<file>
- 指向已索引文档的相对链接（../../network/xxx.md 等）→ 站内路由链接 #/doc/<file>
- 指向 raw/ 的相对链接（**本地存档** 等）只保留文本，raw 不对外暴露
- 指向未索引文件的相对 .md 链接降级为纯文本，避免 404
- 输出经 nh3 白名单消毒：剪藏原文里的 <script>/on* 事件等 raw HTML 会被剥离
  （前端以 v-html 注入，Python-Markdown 默认透传 raw HTML，必须消毒）
"""
import re
from pathlib import Path
from urllib.parse import quote, unquote

import markdown
import nh3

from ..indexer import normalize_key, split_frontmatter

WIKILINK_RE = re.compile(r"\[\[([^\[\]|]+)(?:\|([^\[\]]+))?\]\]")
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")

MD_EXTENSIONS = ["extra", "sane_lists", "toc", "pymdownx.tilde"]


def build_link_map(docs) -> dict:
    """归一化标题/文件名 → file 路径，供 wikilink 解析。"""
    link_map = {}
    for d in docs:
        stem = Path(d["file"]).stem
        link_map.setdefault(normalize_key(stem), d["file"])
        link_map.setdefault(normalize_key(d["title"]), d["file"])
    return link_map


def _convert_wikilinks(body: str, link_map: dict) -> str:
    def repl(m):
        target, alias = m.group(1).strip(), m.group(2)
        text = (alias or target).strip()
        file = link_map.get(normalize_key(target))
        if file:
            return f'<a class="wikilink" href="#/doc/{quote(file)}">{text}</a>'
        return f'<span class="wikilink-missing">{text}</span>'
    return WIKILINK_RE.sub(repl, body)


def _strip_raw_links(body: str, md_path: Path, kb_root: Path, indexed_files: set) -> str:
    """raw/ 及未索引的相对 .md 链接降级为纯文本；指向已索引文档的相对链接转站内路由。"""
    def repl(m):
        text, href = m.group(1), m.group(2)
        if "/raw/" in href or href.startswith("../raw"):
            return text
        if href.startswith("../") and href.endswith(".md"):
            target = (md_path.parent / unquote(href)).resolve()
            try:
                rel = target.relative_to(kb_root).as_posix()
            except ValueError:
                return text
            if rel in indexed_files:
                return f'<a class="wikilink" href="#/doc/{quote(rel)}">{text}</a>'
            return text
        return m.group(0)
    return MD_LINK_RE.sub(repl, body)


def render_document(md_path: Path, link_map: dict, kb_root: Path, indexed_files: set) -> str:
    text = md_path.read_text(encoding="utf-8")
    _, body = split_frontmatter(text)
    body = _strip_raw_links(body, md_path, kb_root, indexed_files)
    body = _convert_wikilinks(body, link_map)
    html = markdown.markdown(body, extensions=MD_EXTENSIONS, output_format="html5")
    return _sanitize(html)


# nh3 默认白名单已覆盖排版所需标签（p/a/h1-h6/list/code/pre/blockquote/table/img 等），
# 剥离 script/iframe/on* 事件/javascript: 协议；图片仅允许站内 raw/assets 相对路径。
_SANITIZE_KWARGS = {
    "url_schemes": {"http", "https", "mailto"},
    "link_rel": "noopener noreferrer",
    "attributes": {
        "a": {"href", "class"},
        "img": {"src", "alt", "title"},
        "code": {"class"},
        "span": {"class"},
    },
}


def _sanitize(html: str) -> str:
    clean = nh3.clean(html, **_SANITIZE_KWARGS)
    # 图片 src 白名单：仅站内相对路径（raw/assets 等），外链图降级为无 src
    def fix_img(m):
        tag = m.group(0)
        src_m = re.search(r'src="([^"]*)"', tag)
        if src_m and not src_m.group(1).startswith(("/", "./", "../")):
            tag = tag.replace(src_m.group(0), 'src=""')
        return tag
    return re.sub(r"<img\b[^>]*>", fix_img, clean)
