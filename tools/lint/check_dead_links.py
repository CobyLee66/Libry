#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扩展 lint：lint_wiki.py 不覆盖的三类问题

1. 正文相对 markdown 链接死链（**允许文件名含空格**）
2. `sources:` frontmatter 引用是否可达（全库 basename 索引）
3. frontmatter YAML 是否可解析、必需字段是否齐全、是否残留双 frontmatter

用法：python3 check_dead_links.py [vault_root]   （默认 $KB_ROOT 或当前目录）
退出码：0 无问题 / 1 有问题（有问题的行会打印 file:line）
"""
import os
import re
import sys
import glob
import collections

ROOT = os.path.abspath(os.path.expanduser(
    sys.argv[1] if len(sys.argv) > 1
    else os.environ.get('KB_ROOT') or os.getcwd()))
os.chdir(ROOT)
WIKI = os.path.join(ROOT, 'wiki')
SKIP_DIRS = {'.git', 'node_modules', 'webapp', 'output', 'logs', '.venv', 'raw', '.libry'}
REQ_FIELDS = ('tags', 'sources', 'created', 'updated')

# 全库 basename 索引（用于 sources 可达性判定）
name_index = {}
for r, ds, fs in os.walk('.'):
    ds[:] = [d for d in ds if d not in SKIP_DIRS and not d.startswith('.')]
    for f in fs:
        name_index.setdefault(f, os.path.join(r, f))

LINK = re.compile(r'\[([^\]]*)\]\(([^)\n]+)\)')  # 注意：不要用 [^)\s]+ —— 会漏掉含空格的文件名

strings_mod = None
try:
    import yaml
except ImportError:
    yaml = None
    print('! PyYAML 不可用（请用装了 libry 的解释器跑本脚本，如引擎 venv 的 python）')

report = collections.defaultdict(list)
for p in sorted(glob.glob(os.path.join(WIKI, '*', '*.md'))):
    txt = open(p, encoding='utf-8').read()
    relp = os.path.relpath(p, ROOT)
    for n, line in enumerate(txt.splitlines(), 1):
        for m in LINK.finditer(line):
            tgt = m.group(2).strip()
            if tgt.startswith('<') and tgt.endswith('>'):
                tgt = tgt[1:-1]
            if tgt.startswith(('http', '#', 'mailto')):
                continue
            full = os.path.normpath(os.path.join(os.path.dirname(p), tgt))
            if not os.path.exists(full):
                report['dead_link'].append(f'{relp}:{n}  ->  {tgt}')

    if re.match(r'^---\n.*?\n---\n\n+---\n', txt, re.S):
        report['double_frontmatter'].append(relp)

    m = re.match(r'^---\n(.*?)\n---\n', txt, re.S)
    if not m:
        report['frontmatter'].append(f'{relp}  (无 frontmatter)')
        continue
    if yaml is None:
        continue
    try:
        fm = yaml.safe_load(m.group(1))
    except Exception as e:
        report['frontmatter'].append(f'{relp}  (YAML 解析失败: {str(e).splitlines()[0][:70]})')
        continue
    for f in REQ_FIELDS:
        if f not in fm or fm[f] in (None, ''):
            report['frontmatter'].append(f'{relp}  (缺 {f})')
    for it in (fm.get('sources') or []):
        if not isinstance(it, str) or not it.endswith(('.md', '.txt')) or it.startswith('~'):
            continue
        # git 历史引用（如 548dba3^:raw/...）是刻意的溯源注记，不要求文件现存
        if re.search(r'\b[0-9a-f]{7,}\^?:', it):
            continue
        base = os.path.basename(it.replace('\\', '/'))
        if base not in name_index and not os.path.exists(it):
            report['stale_sources'].append(f'{relp}  ->  {it}')

TITLES = {
    'dead_link': '正文相对链接死链',
    'stale_sources': 'sources: 引用不可达',
    'frontmatter': 'frontmatter 问题',
    'double_frontmatter': '重复 frontmatter 块',
}
total = 0
for k, t in TITLES.items():
    items = report[k]
    total += len(items)
    print(f'== {t}: {len(items)}')
    for x in items[:40]:
        print('   ', x)
    if len(items) > 40:
        print(f'    ... 另有 {len(items) - 40} 条')
print('TOTAL', total)
sys.exit(1 if total else 0)
