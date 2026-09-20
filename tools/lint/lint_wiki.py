#!/usr/bin/env python3
"""Full health-check for a Libry second-brain wiki.

Usage:  python3 lint_wiki.py [vault_root]
Default vault_root: $KB_ROOT or current directory

Checks (Obsidian-aware, matches real Obsidian resolution rules):
  - Broken wikilinks: targets with no matching filename OR frontmatter alias
    (Obsidian matches case-insensitively but KEEPS spaces/hyphens; the old
    "delete all spaces/hyphens" normalization was too loose and reported
    0 broken while 165 links were actually broken)
  - Needs-alias links: link matches a page title only after stripping a
    trailing parenthetical (e.g. [[信号传递]] vs 信号传递 (Signalling)) —
    broken in Obsidian unless an alias exists
  - Orphan pages: no inbound wikilinks from other pages or index.md
  - Index entries pointing to missing pages
  - Missing YAML frontmatter
  - Raw file-path links ([[../sources/...]]) instead of page-title wikilinks
  - Markdown links to wiki paths ([text](sources/x.md))
  - Untitled H1 check: files whose H1 is "# untitled" (webapp shows untitled)

Exit code 0 with all-zero counts = healthy wiki.
"""
import re, os, sys, unicodedata
from collections import Counter

VAULT_ROOT = None
if len(sys.argv) > 1:
    VAULT_ROOT = os.path.abspath(os.path.expanduser(sys.argv[1]))
elif os.environ.get("KB_ROOT"):
    VAULT_ROOT = os.path.abspath(os.path.expanduser(os.environ["KB_ROOT"]))
else:
    VAULT_ROOT = os.getcwd()
WIKI = os.path.join(VAULT_ROOT, "wiki")
ROOT = WIKI

def _content_dirs(vault):
    try:
        import tomllib
        with open(os.path.join(vault, "libry.toml"), "rb") as fh:
            data = tomllib.load(fh)
    except Exception:
        return []
    dirs = data.get("content_dirs") or []
    if isinstance(dirs, str):
        dirs = [dirs]
    return [str(d).strip("/") for d in dirs if str(d).strip("/")]

pages = []  # (subdir, filename, title, path)
title_to_file = {}


def normalize(s):
    """Matching key aligned with webapp/indexer.normalize_key: case-insensitive,
    strip ALL non-alphanumeric chars (keep CJK). The webapp is the primary
    reader now (2026-08-23); Obsidian's stricter filename rules no longer
    govern link resolution. Keeping this in sync with webapp means lint
    reports the links users actually experience (e.g. [[中文标题式链接]] still
    resolves to a kebab-case filename page).
    """
    return re.sub(r'[^\w一-鿿]+', '', unicodedata.normalize('NFKC', s).lower())


def frontmatter_aliases(content):
    """Parse `aliases:` from YAML frontmatter (block or inline list form)."""
    fm = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not fm:
        return []
    block = fm.group(1)
    aliases = []
    m = re.search(r'^aliases:\n((?:[ \t]+- .*\n?)*)', block, re.MULTILINE)
    if m:
        for line in m.group(1).splitlines():
            line = line.strip()
            if line.startswith('- '):
                aliases.append(line[2:].strip().strip('"\''))
    else:
        m2 = re.search(r'^aliases:\s*\[(.*?)\]', block, re.MULTILINE)
        if m2:
            aliases.extend(a.strip().strip('"\'') for a in m2.group(1).split(','))
    return aliases


for sub in ['sources', 'entities', 'concepts', 'synthesis']:
    d = os.path.join(WIKI, sub)
    if not os.path.isdir(d):
        continue
    for fn in sorted(os.listdir(d)):
        if not fn.endswith('.md'):
            continue
        path = os.path.join(d, fn)
        content = open(path, encoding='utf-8').read()
        m = re.search(r'^#\s+(.+)$', content, re.M)
        title = m.group(1).strip() if m else fn[:-3]
        pages.append((sub, fn, title, path))
        # filename itself resolves; setdefault (NOT direct assignment) so the
        # FIRST registration wins on normalize collisions — same as webapp
        # build_link_map. wiki/ pages are scanned before top-level archive
        # dirs, so a wiki page keeps priority over a top-level doc whose
        # filename normalizes identically (e.g. SSH-使用与隧道技术指南 vs
        # SSH使用与隧道技术指南).
        title_to_file.setdefault(normalize(fn[:-3]), fn[:-3])
        # H1 title always resolves (webapp build_link_map registers both
        # filename stem and title unconditionally). setdefault keeps the
        # first registration on collision, same as webapp.
        title_to_file.setdefault(normalize(title), fn[:-3])
        # frontmatter aliases resolve
        for a in frontmatter_aliases(content):
            title_to_file.setdefault(normalize(a), fn[:-3])

# ALSO register pages from the vault root and top-level category dirs
# (ai-agent/, network/, finance/, language/, ...). Obsidian resolves links
# against the WHOLE vault, and aliases can live in any file's frontmatter.
# The old script only scanned wiki/{sources,entities,concepts,synthesis}/
# and wrongly reported broken links for aliases defined outside wiki/.
# IMPORTANT (2026-08-23): only scan KNOWLEDGE-BASE content dirs. webapp/,
# output/, raw/, logs/ are NOT wiki content — scanning them (webapp holds
# node_modules/.venv markdown docs) produced hundreds of false orphans and
# missing-frontmatter reports. webapp/indexer.py uses CONTENT_DIRS for the
# same purpose (type=archive); keep this list in sync with it.
CONTENT_DIRS = _content_dirs(VAULT_ROOT)
# subdirs that must never be treated as wiki content even if they hold .md
SKIP_DIRS = {".git", ".obsidian", ".trash", "raw", "wiki", "webapp",
             "output", "logs", "node_modules", ".venv", "__pycache__",
             "cache", "data", ".libry", "libry"}
if os.path.dirname(WIKI) != WIKI:
    vault_root = VAULT_ROOT
    for root, dirs, files in os.walk(vault_root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        rel_root = os.path.relpath(root, vault_root)
        if rel_root == '.':
            continue
        top = rel_root.split('/')[0]
        # only content dirs (skip anything outside CONTENT_DIRS at depth 1,
        # but still descend into their subdirs)
        if rel_root.count('/') == 0 and top not in CONTENT_DIRS:
            dirs[:] = []
            continue
        for fn in sorted(files):
            if not fn.endswith('.md') or fn in ('index.md', 'AGENTS.md', 'pending.md'):
                continue
            path = os.path.join(root, fn)
            content = open(path, encoding='utf-8').read()
            m = re.search(r'^#\s+(.+)$', content, re.M)
            title = m.group(1).strip() if m else fn[:-3]
            pages.append((top, fn, title, path))
            title_to_file.setdefault(normalize(fn[:-3]), fn[:-3])
            title_to_file.setdefault(normalize(title), fn[:-3])
            for a in frontmatter_aliases(content):
                title_to_file.setdefault(normalize(a), fn[:-3])


def extract_target(text):
    """Extract wikilink target from [[...]] content, honoring \\| escapes."""
    parts = []
    i = 0
    while i < len(text):
        if text[i] == '\\' and i + 1 < len(text) and text[i + 1] == '|':
            parts.append('|')
            i += 2
        elif text[i] == '|':
            return ''.join(parts), text[i + 1:]  # alias separator
        else:
            parts.append(text[i])
            i += 1
    return ''.join(parts), None


def strip_code_blocks(content):
    """Remove fenced code blocks and inline code so examples aren't scanned."""
    content = re.sub(r'```.*?```', '', content, flags=re.S)
    content = re.sub(r'`[^`]*`', '', content)
    return content


link_re = re.compile(r'\[\[([^\]]+)\]\]')
raw_path_re = re.compile(r'^((?:\.\./)+|/)')

broken = {}
needs_alias = {}
inbound = {}
no_frontmatter = []
raw_path_links = []
md_links = []
untitled_h1 = []

for sub, fn, title, path in pages:
    content = open(path, encoding='utf-8').read()
    if not content.startswith('---'):
        no_frontmatter.append((sub, fn))
    # Untitled H1 check: H1 is exactly "# untitled" (case-insensitive)
    m = re.search(r'^#\s+(.+)$', content, re.M)
    if m and m.group(1).strip().lower() == 'untitled':
        untitled_h1.append((sub, fn, path))
    scan = strip_code_blocks(content)
    for m in link_re.finditer(scan):
        target, alias = extract_target(m.group(1))
        target = target.strip()
        if not target:
            continue
        if raw_path_re.match(target):
            raw_path_links.append((fn, target))
            continue
        key = normalize(target)
        if key in title_to_file:
            inbound.setdefault(title_to_file[key], set()).add(fn)
            continue
        # short-form fallback: strip trailing parenthetical -> needs alias
        short = re.sub(r'\s*[（(].*?[)）]\s*$', '', target)
        short_key = normalize(short)
        if short_key in title_to_file and short_key != key:
            needs_alias.setdefault(target, []).append(fn)
        else:
            broken.setdefault(target, []).append(fn)
    # markdown links to knowledge-base files count as inbound too
    # ([text](../../network/xxx.md) etc. — the clickable 原文存档 pattern).
    # Matches links whose target resolves inside the vault (wiki/ or top-level
    # content dirs) but NOT raw/ (raw never gets a page) and NOT webapp/.
    for m in re.finditer(r'\[[^\]]*\]\(([^)]+\.md)\)', scan):
        href = m.group(1)
        if '/raw/' in href or href.startswith('../raw'):
            continue
        target = os.path.normpath(os.path.join(os.path.dirname(path), href))
        try:
            rel = os.path.relpath(target, vault_root)
        except (NameError, ValueError):
            continue
        if rel.startswith('..') or rel.startswith('/'):
            continue
        nk = normalize(os.path.splitext(os.path.basename(target))[0])
        if nk in title_to_file:
            inbound.setdefault(title_to_file[nk], set()).add(fn)
    for m in re.finditer(r'\[([^\]]*)\]\((?:\x2e\x2e/)*(sources|entities|concepts|synthesis)/[^)]+\.md\)', content):
        md_links.append((fn, m.group(0)))

# index.md links count as inbound
# index.md lives at the vault ROOT (top-level), not under wiki/
candidate_index = os.path.join(WIKI, 'index.md')
if not os.path.exists(candidate_index):
    vault_root = VAULT_ROOT
    candidate_index = os.path.join(vault_root, 'index.md')
index_path = candidate_index
index_content = open(index_path, encoding='utf-8').read() if os.path.exists(index_path) else ''
for m in link_re.finditer(index_content):
    target, alias = extract_target(m.group(1))
    key = normalize(target.strip())
    if key in title_to_file:
        inbound.setdefault(title_to_file[key], set()).add('index.md')

# Orphans: wiki pages (sources/entities/concepts/synthesis) must have an
# inbound link from another page OR index.md. Top-level archive docs
# (ai-agent/, network/, ...) are NOT expected to be wikilinked the same way —
# they are referenced via clickable markdown links (**本地存档**) from their
# source pages, and index.md often links them by title. Treat a top-level doc
# as non-orphan if it has ANY inbound (wikilink OR markdown link OR index).
def _is_wiki_page(sub: str) -> bool:
    return sub in ('sources', 'entities', 'concepts', 'synthesis')

orphans = []
archive_orphans = []
for sub, fn, title, _ in pages:
    if not inbound.get(fn[:-3]):
        if _is_wiki_page(sub):
            orphans.append((sub, fn, title))
        else:
            archive_orphans.append((sub, fn, title))

index_missing = []
index_needs_alias = []
for m in link_re.finditer(index_content):
    target, alias = extract_target(m.group(1))
    key = normalize(target.strip())
    if key in title_to_file:
        continue
    short = re.sub(r'\s*[（(].*?[)）]\s*$', '', target.strip())
    if normalize(short) in title_to_file:
        index_needs_alias.append(target.strip())
    else:
        index_missing.append(target.strip())

print(f"Pages: {len(pages)} "
      f"(sources: {sum(1 for p in pages if p[0]=='sources')}, "
      f"entities: {sum(1 for p in pages if p[0]=='entities')}, "
      f"concepts: {sum(1 for p in pages if p[0]=='concepts')}, "
      f"synthesis: {sum(1 for p in pages if p[0]=='synthesis')})")
print(f"Broken wikilinks: {sum(len(v) for v in broken.values())} occurrences / {len(broken)} targets")
for t, files in sorted(broken.items()):
    print(f"  [[{t}]] <- {files}")
print(f"Needs-alias links (trailing-parenthetical match, broken in Obsidian): "
      f"{sum(len(v) for v in needs_alias.values())} occurrences / {len(needs_alias)} targets")
for t, files in sorted(needs_alias.items()):
    print(f"  [[{t}]] <- {files}")
print(f"Orphan pages: {len(orphans)}")
for sub, fn, title in orphans:
    print(f"  [{sub}] {fn} ({title})")
print(f"Top-level archive docs without inbound (info, not error): {len(archive_orphans)}")
for sub, fn, title in archive_orphans[:30]:
    print(f"  [{sub}] {fn} ({title})")
if len(archive_orphans) > 30:
    print(f"  ... and {len(archive_orphans)-30} more")
print(f"Index entries missing targets: {len(index_missing)}")
for t in index_missing:
    print(f"  [[{t}]]")
print(f"Index entries needing alias (trailing-parenthetical): {len(index_needs_alias)}")
for t in index_needs_alias:
    print(f"  [[{t}]]")
# frontmatter is required for wiki pages; top-level archive docs are plain
# documents (self-authored guides / raw articles) and don't need frontmatter.
wiki_no_fm = [(s, f) for s, f in no_frontmatter if _is_wiki_page(s)]
print(f"Missing frontmatter (wiki pages only): {len(wiki_no_fm)}")
for sub, fn in wiki_no_fm:
    print(f"  [{sub}] {fn}")
print(f"Raw path links: {len(raw_path_links)}")
for fn, t in raw_path_links:
    print(f"  {fn}: {t}")
print(f"Markdown links to wiki paths: {len(md_links)}")
for fn, t in md_links:
    print(f"  {fn}: {t}")

# Untitled H1 check (2026-08-25): files whose H1 is "# untitled" —
# opencli zhihu download doesn't fetch the question title, so the file H1
# defaults to "# untitled". These show up as "untitled" in webapp lists and
# search, making them unfindable. Must be fixed before ingest is complete.
print(f"Untitled H1 (must fix before ingest complete): {len(untitled_h1)}")
for sub, fn, path in untitled_h1:
    print(f"  [{sub}] {fn} -> {os.path.relpath(path, VAULT_ROOT)}")

# index duplicates (rough check by exact [[Title]] text)
entries = re.findall(r'^- \[\[(.+?)\]\]', index_content, re.M)
dups = [k for k, v in Counter(entries).items() if v > 1]
print(f"Index duplicate entries: {dups if dups else 'none'}")
