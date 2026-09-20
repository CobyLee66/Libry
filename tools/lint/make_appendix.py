#!/usr/bin/env python3
"""Generate / verify a wiki source-page appendix (full original text, headings demoted one level).

Rule (vault AGENTS.md convention): source pages embed the full original under
`## 附录：原文全文（<版本/日期>）`, with every original heading demoted one level, and must be
verified lossless ("diff 校验无截断"). Do NOT hand-retype hundreds of lines — generate, then verify.

Usage:
  python3 make_appendix.py <source.md> -o <appendix.md>
      # demote headings one level (prepend one '#' to each heading line), keep ALL other lines as-is

  python3 make_appendix.py --verify <wiki_page.md> <appendix_file.md>
      # verify the wiki page's appendix section (from the appendix file's first line onward)
      # equals the appendix file line-for-line; exit 0 on match, 1 on any diff

Real-world use (2026-09-07 doc-split sync): two source docs (328 / 371 lines) regenerated this
way and appended after the 提炼 section; --verify matched exactly for both. Then grep inbound
wikilinks + old chapter-number citations and remap them to the split target (see SKILL.md
"同步源文档变更" section).
"""
import argparse
import pathlib
import re
import sys


def demote(src_text: str) -> str:
    out = []
    for line in src_text.splitlines(keepends=True):
        if re.match(r"^#{1,6}\s", line):
            line = "#" + line
        out.append(line)
    return "".join(out)


def verify(wiki_page: pathlib.Path, appendix: pathlib.Path) -> bool:
    page_lines = wiki_page.read_text(encoding="utf-8").splitlines()
    apx_lines = appendix.read_text(encoding="utf-8").splitlines()
    if not apx_lines:
        print("appendix file is empty")
        return False
    h1 = apx_lines[0]
    try:
        idx = page_lines.index(h1)
    except ValueError:
        print(f"appendix first line not found in wiki page: {h1!r}")
        return False
    got = page_lines[idx:]
    if got == apx_lines:
        print(f"OK: appendix matches from wiki line {idx + 1} ({len(got)} lines)")
        return True
    for i, (a, b) in enumerate(zip(got, apx_lines)):
        if a != b:
            print(f"DIFF at offset {i}: page={a!r} appendix={b!r}")
            break
    print(f"length: wiki-part={len(got)} appendix={len(apx_lines)}")
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("-o", "--output")
    ap.add_argument("--verify", action="store_true", help="compare wiki page appendix section vs appendix file")
    args = ap.parse_args()
    if args.verify:
        if not args.output:
            ap.error("--verify needs <wiki_page.md> as source and <appendix_file.md> as -o")
        sys.exit(0 if verify(pathlib.Path(args.source), pathlib.Path(args.output)) else 1)
    result = demote(pathlib.Path(args.source).read_text(encoding="utf-8"))
    if args.output:
        pathlib.Path(args.output).write_text(result, encoding="utf-8")
        print(f"wrote {args.output} ({len(result.splitlines())} lines)")
    else:
        sys.stdout.write(result)


if __name__ == "__main__":
    main()
