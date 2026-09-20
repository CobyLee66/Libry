#!/usr/bin/env python3
"""Strict index.md entry check — classify every [[link]] in index.md as:
  - FILE:     resolves to a filename (normalize_key match)
  - H1-ONLY:  resolves only via H1 title (filename differs) — latent mismatch
  - MISSING:  no file or H1 anywhere in the vault

Lint reports "Index entries missing targets: 0" because webapp registers BOTH
the filename stem AND the H1 title as resolution keys. But an entry that only
matches via H1 (e.g. [[催产素（Oxytocin）]] → file 催产素.md whose H1 is
"催产素（Oxytocin）") is a filename-level mismatch that silently breaks once
the file is renamed or the H1 edited. Run this to catch the latent mismatches
lint misses. The durable fix is: unify the index link text to the filename
(drop the parenthetical English suffix), keep the suffix in H1 or aliases.

Usage: python3 check_index_strict.py [vault_root]
Default vault_root: $KB_ROOT or current directory
"""
import re, os, sys, unicodedata

VAULT = os.path.abspath(os.path.expanduser(
    sys.argv[1] if len(sys.argv) > 1
    else os.environ.get('KB_ROOT') or os.getcwd()))

def normalize_key(s):
    return re.sub(r'[^\w\u4e00-\u9fff]+', '', unicodedata.normalize('NFKC', s).lower())

filenames = {}
h1s = {}
for root, dirs, files in os.walk(VAULT):
    if any(x in root for x in ['/webapp', '/raw', '/.git', 'node_modules', '/output', '/logs', '/data', '/cache', '/.libry']):
        continue
    for f in files:
        if not f.endswith('.md'):
            continue
        p = os.path.join(root, f)
        stem = f[:-3]
        filenames.setdefault(normalize_key(stem), p)
        try:
            t = open(p, encoding='utf-8').read()
            m = re.search(r'^#\s+(.+)$', t, re.M)
            if m:
                h1s.setdefault(normalize_key(m.group(1).strip()), p)
        except Exception:
            pass

idx_path = os.path.join(VAULT, 'index.md')
idx = open(idx_path, encoding='utf-8').read()
no_file = []
no_h1 = []
resolved = []
for m in re.finditer(r'^- \[\[([^\]|]+)', idx, re.M):
    target = m.group(1).strip()
    k = normalize_key(target)
    if k in filenames:
        resolved.append(target)
    elif k in h1s:
        no_file.append((target, h1s[k]))
    else:
        no_h1.append(target)

print(f"index.md entries: {len(resolved) + len(no_file) + len(no_h1)}")
print(f"filename hit: {len(resolved)}")
print(f"H1-only (filename differs, latent mismatch): {len(no_file)}")
for t, p in no_file:
    print(f"  [[{t}]] -> {os.path.relpath(p, VAULT)}")
print(f"MISSING: {len(no_h1)}")
for t in no_h1:
    print(f"  [[{t}]]")
