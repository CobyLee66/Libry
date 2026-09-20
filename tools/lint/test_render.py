#!/usr/bin/env python3
"""Render a markdown file through the webapp pipeline and report structural anomalies.

Usage:
    python test_render.py <path-to-md>    （需已安装 libry 包）

Detects the three common "missing blank line" rendering traps in
Python-Markdown (webapp render.py, extensions extra/sane_lists/toc/pymdownx.tilde):

  1. Table swallowed into <p> (raw pipes stay visible, no <table> generated)
  2. List markers (- / 1. ) left as plain text inside <p>
  3. Setext h2 trap: a paragraph line followed by --- renders as <h2>, not <hr>

Also prints counts so you can confirm <table>/<ul> came back after fixing.
Exit code 0 = no anomalies found.
"""
import re
import sys
from pathlib import Path

from libry.server.render import render_document

if len(sys.argv) < 2:
    print("usage: python test_render.py <markdown-file>")
    sys.exit(2)

md_path = Path(sys.argv[1]).resolve()
assert md_path.exists(), f"not found: {md_path}"

# KB root = nearest ancestor containing wiki/
kb_root = md_path
while not (kb_root / "wiki").exists() and kb_root != kb_root.parent:
    kb_root = kb_root.parent

html = render_document(md_path, {}, kb_root, set())
problems = []

# 1) raw pipes inside a paragraph -> table was swallowed
for i, m in enumerate(re.finditer(r"<p>(.*?)</p>", html, re.S), 1):
    stripped = re.sub(r"<[^>]+>", "", m.group(1))
    piped = [l for l in stripped.split("\n") if "|" in l]
    if piped:
        problems.append(f"<p>#{i} 含竖线 → 表格被吞进段落（表格前/后缺空行）: {piped[0].strip()[:60]}")

# 2) list markers inside a paragraph -> list was swallowed
for i, m in enumerate(re.finditer(r"<p>(.*?)</p>", html, re.S), 1):
    stripped = re.sub(r"<[^>]+>", "", m.group(1))
    for line in stripped.split("\n"):
        s = line.lstrip()
        if re.match(r"^(-|\d+\.)\s", s):
            problems.append(f"<p>#{i} 含列表标记 → 列表被吞进段落（列表前缺空行）: {s[:60]}")
            break

# 3) setext h2 trap: <h2> text that matches no real '## ' source line
src = md_path.read_text(encoding="utf-8")
real_h2 = {re.sub(r"[*_`]", "", m.group(1)).strip()
           for m in re.finditer(r"^##\s+(.+)$", src, re.M)}
for m in re.finditer(r"<h2>(.*?)</h2>", html, re.S):
    text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
    if text not in real_h2:
        problems.append(f"setext h2 陷阱 → 正文被误渲染为 <h2>（该行前缺空行，紧跟 ---）: {text[:60]}")

print(f"文件: {md_path}")
print(f"<table>: {html.count('<table>')} | ul/ol: {html.count('<ul>') + html.count('<ol')} | "
      f"h2: {len(re.findall('<h2>', html))} (源文件 ## 行: {len(real_h2)})")
if problems:
    print("发现异常:")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("OK: 无渲染异常")