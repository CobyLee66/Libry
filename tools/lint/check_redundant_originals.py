#!/usr/bin/env python3
"""Scan all top-level content-dir .md files and check if their content is
fully covered by the corresponding wiki/sources/ page's 📖 结构化全文 /
📖 原文 section. If fully covered → the original file is redundant and
can be deleted (source page already has the full text).

Outputs a table: file | source page | coverage% | verdict (delete/keep)
"""
import re, os, sys

VAULT = os.path.abspath(os.path.expanduser(
    sys.argv[1] if len(sys.argv) > 1
    else os.environ.get('KB_ROOT') or os.getcwd()))
try:
    import tomllib
    with open(os.path.join(VAULT, 'libry.toml'), 'rb') as fh:
        _dirs = tomllib.load(fh).get('content_dirs') or []
    if isinstance(_dirs, str):
        _dirs = [_dirs]
    CONTENT_DIRS = [str(d).strip('/') for d in _dirs if str(d).strip('/')]
except Exception:
    CONTENT_DIRS = []
WIKI_SOURCES = os.path.join(VAULT, "wiki", "sources")

def rawbody(path):
    """Extract article body from a top-level .md file (strip frontmatter,
    # H1, > blockquote metadata lines)."""
    t = open(path, encoding='utf-8').read()
    t = re.sub(r'^---\n.*?\n---\n', '', t, flags=re.S)
    t = re.sub(r'^# .*\n', '', t)
    t = re.sub(r'^>\s*.*\n', '', t, flags=re.M)
    return t

def source_fulltext_section(src_path):
    """Extract the 📖 结构化全文 or 📖 原文 section from a source page."""
    t = open(src_path, encoding='utf-8').read()
    m = re.search(r'## 📖\s*(?:结构化全文|原文|全文)(.*)', t, re.S)
    if m:
        return m.group(1)
    return ''

def clean(s):
    return re.sub(r'[\s\u201c\u201d"\'（）(),，.;;：:——\-\[\]#*>|!？!?…\n\r\t ]', '', s)

def find_source_for(raw_path, raw_rel):
    """Try to find the wiki/sources/ page that references this raw file.
    Strategy: check each source page's frontmatter sources: field and
    原文存档/本地存档 body links for the raw filename."""
    raw_fn = os.path.basename(raw_path)
    raw_stem = raw_fn[:-3] if raw_fn.endswith('.md') else raw_fn
    for sf in os.listdir(WIKI_SOURCES):
        if not sf.endswith('.md'):
            continue
        sp = os.path.join(WIKI_SOURCES, sf)
        t = open(sp, encoding='utf-8').read()
        # check frontmatter sources: field
        fm_match = re.search(r'^sources:\s*\[([^\]]*)\]', t, re.M)
        if fm_match:
            sources_val = fm_match.group(1)
            if raw_fn in sources_val or raw_rel in sources_val:
                return sp
        # check body 原文存档/本地存档 markdown link
        body_match = re.search(r'\*\*(?:原文存档|本地存档|Source)\*\*[^]]*\]\(([^)]+)\)', t)
        if body_match:
            href = body_match.group(1)
            if raw_fn in href or raw_stem in href:
                return sp
        # check if source page filename relates to raw filename
        # (fuzzy: both contain same key Chinese chars)
    return None

# Collect all top-level .md files
candidates = []
for d in CONTENT_DIRS:
    dirpath = os.path.join(VAULT, d)
    if not os.path.isdir(dirpath):
        continue
    for root, dirs, files in os.walk(dirpath):
        dirs[:] = [x for x in dirs if x not in ('monthly-report',)]
        for fn in files:
            if not fn.endswith('.md') or fn in ('index.md', 'AGENTS.md', 'pending.md'):
                continue
            candidates.append(os.path.join(root, fn))

print(f"Top-level .md files: {len(candidates)}")
print(f"{'File':<55} {'Source page':<45} {'Cov%':>5} {'Verdict':>8}")
print("-" * 120)

delete_candidates = []
keep_candidates = []
no_source = []

for raw_path in sorted(candidates):
    raw_rel = os.path.relpath(raw_path, VAULT)
    raw_fn = os.path.basename(raw_path)
    src_path = find_source_for(raw_path, raw_rel)
    if not src_path:
        no_source.append(raw_rel)
        continue
    rb = clean(rawbody(raw_path))
    sec = clean(source_fulltext_section(src_path))
    if not rb or len(rb) < 50:
        # too short to judge, skip
        continue
    # coverage: head 20 chars in source AND tail 20 chars in source AND
    # source section length >= 80% of raw body length
    head_in = rb[:20] in sec if len(rb) >= 20 else True
    tail_in = rb[-20:] in sec if len(rb) >= 20 else True
    ratio = len(sec) / len(rb) if len(rb) > 0 else 1.0
    fully_covered = head_in and tail_in and ratio >= 0.95
    verdict = "DELETE" if fully_covered else "KEEP"
    src_fn = os.path.basename(src_path)
    print(f"{raw_fn:<55} {src_fn[:43]:<45} {ratio*100:>5.0f}% {verdict:>8}")
    if fully_covered:
        delete_candidates.append((raw_path, src_path))
    else:
        keep_candidates.append((raw_path, src_path, ratio, head_in, tail_in))

print("\n=== SUMMARY ===")
print(f"DELETE (source fully covers original): {len(delete_candidates)}")
print(f"KEEP (source is condensed/partial): {len(keep_candidates)}")
print(f"NO SOURCE PAGE FOUND: {len(no_source)}")
if no_source:
    print("  No source:")
    for r in no_source:
        print(f"    {r}")