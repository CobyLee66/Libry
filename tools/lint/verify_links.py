#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Whole-vault wikilink verification under webapp resolution rules.

The webapp (webapp/server/render.py build_link_map) resolves [[X]] against
BOTH the filename stem and the page H1 title, using normalize_key: NFKC,
lowercase, strip ALL non-alphanumeric chars (keep CJK). This script mirrors
those rules so it reports links exactly as users experience them in the
webapp — e.g. [[催产素（Oxytocin）]] resolves to file 催产素.md via its H1.

Run after ANY rename/dedup/alias pass to prove no link is left dangling.

Usage:  python3 verify_links.py [vault_root]
Default vault_root: $KB_ROOT or current directory

Exit code 0 = all links resolve. Prints unresolved links otherwise.
Skips: raw/ (immutable source), .git/.trash, code fences + inline code,
wiki/log.md (history log contains template examples).
"""
import os
import re
import sys
import unicodedata

VAULT = os.path.abspath(os.path.expanduser(
    sys.argv[1] if len(sys.argv) > 1
    else os.environ.get("KB_ROOT") or os.getcwd()))
INDEX = os.path.join(VAULT, "index.md")


def link_key(s):
    # Aligned with webapp/indexer.normalize_key + lint_wiki.normalize: NFKC,
    # lowercase, strip ALL non-alphanumeric (keep CJK). The webapp is the
    # primary reader; link resolution follows webapp rules so this check
    # reports what users actually experience.
    s = unicodedata.normalize("NFKC", s).lower()
    return re.sub(r"[^\w一-鿿]+", "", s)


# 1. Collect every .md filename in the vault (exclude raw/, .git, config)
resolvable = {}  # link_key -> [rel paths]
pages = []       # (rel_dir, abs_path)
for root, dirs, files in os.walk(VAULT):
    dirs[:] = [d for d in dirs if d not in (".git", ".trash")]
    rel_root = os.path.relpath(root, VAULT)
    if rel_root.startswith("raw"):
        continue
    for f in files:
        if not f.endswith(".md") or f in ("AGENTS.md", "pending.md") or f.startswith(".lint"):
            continue
        path = os.path.join(root, f)
        rel = os.path.relpath(path, VAULT)
        resolvable.setdefault(link_key(f[:-3]), []).append(rel)
        # H1 title also resolves (webapp build_link_map registers title too)
        try:
            with open(path, encoding="utf-8") as fh:
                head = fh.read(2000)
        except OSError:
            head = ""
        m = re.search(r"^#\s+(.+)$", head, re.M)
        if m:
            resolvable.setdefault(link_key(m.group(1).strip()), []).append(rel)
        pages.append((rel, path))

# 2. Scan links: index.md + wiki pages + top-level archive docs.
# Archive docs (type=archive, e.g. wizard-finance/*.md) are raw source
# articles: their internal wikilinks may point to concepts that don't have
# wiki pages yet (uncreated-link state). Those are reported as INFO, not
# failures — only wiki/ pages and index.md must have 0 unresolved.
link_re = re.compile(r"\[\[([^\]]+)\]\]")
unresolved = []      # wiki pages + index: failures
archive_unresolved = []  # archive docs: info
total = 0
WIKI_PREFIX = os.path.join("wiki", "")  # "wiki/"
files_to_check = [INDEX] + [p for _, p in pages if "log.md" not in p]
for path in files_to_check:
    rel = os.path.relpath(path, VAULT)
    is_archive = not rel.startswith(WIKI_PREFIX) and rel != os.path.basename(INDEX)
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    # skip fenced/inline code so template examples aren't scanned
    content = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
    content = re.sub(r"`[^`]*`", "", content)
    for m in link_re.finditer(content):
        raw = m.group(1)
        title = raw.split("|")[0].strip()
        if "\\|" in raw:
            title = raw.replace("\\|", "|")  # escaped pipe = literal char
        total += 1
        if link_key(title) not in resolvable:
            if is_archive:
                archive_unresolved.append((rel, title))
            else:
                unresolved.append((rel, title))

print(f"Files indexed: {len(resolvable)}")
print(f"Links checked: {total}, unresolved: {len(unresolved)}"
      f" (+{len(archive_unresolved)} archive-doc links to uncreated concepts, info only)")
if unresolved:
    for src, title in unresolved[:50]:
        print(f"  [{src}] [[{title}]]")
    sys.exit(1)
if archive_unresolved:
    print("Archive-doc uncreated links (not errors):")
    for src, title in archive_unresolved[:15]:
        print(f"  [{src}] [[{title}]]")
    if len(archive_unresolved) > 15:
        print(f"  ... and {len(archive_unresolved)-15} more")
print("OK: all wiki/index links resolve under webapp resolution rules.")
