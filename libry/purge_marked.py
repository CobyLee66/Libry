#!/usr/bin/env python3
"""待删除页面清理：删除 Web 端「标记删除」的页面并机械清理对它们的引用。

触发方：
- 定时 ingest（agent cron，权威端）：agent 按 AGENTS.md 入库流程 step 0 运行本脚本
- 设置页「立即执行删除」（POST /api/deletions/execute，权威端/副本端均可）
- sync_data 合并后对 purged 残留做 --reconcile-only（防本机已删文件复活）

语义（严格机械，不做语义判断）：
1. reconcile：deletions.json 中带 purged 终态、但文件仍残留在本机磁盘且未在
   HEAD 中跟踪（远端已删、本机 reset --soft 后留下的工作区/索引残留）→ 删除。
   文件仍在 HEAD 中跟踪则跳过（可能是删除后有意重建的同名页面）。
2. 对待删除（pending）条目：
   - 路径守卫：必须在 KB_ROOT 下、.md、属于 wiki/{sources,entities,concepts,synthesis}
     或顶层内容目录（libry.toml 的 content_dirs，与 indexer 一致）；文件已不存在则直接转 purged。
   - 删除文件。
   - 引用清理（扫 wiki/**/*.md、content_dirs/**/*.md、顶层 *.md；跳过 wiki/log.md）：
     * 正文 wikilink：[[Title|alias]] → alias，[[Title]] → Title（保句子通顺）
     * index.md：删除 `- [[Title]] — 摘要` 整行
     * frontmatter sources: 数组：移除精确匹配的文件名/相对路径项
   - wiki/log.md 只追加一条 purge 记录（append-only，绝不修改已有条目）。
3. 条目转为 {"purged": ts, "purged_by": KB_ROLE} 终态（跨端 LWW 防复活）。
4. git add -A -- <触及的内容路径>（不含 deletions.json——它由 sync_data 专门提交）。
5. --commit/--push：副本端执行路径用（写权限部署密钥 + fetch/rebase 重试）。

tags.md 的计数列不机械处理，留在报告中交给 lint 校正。

用法：
    python -m libry.purge_marked [--dry-run | --reconcile-only | --commit --push]
输出：stdout 最后一行为 JSON 报告（供 API/agent 消费）。
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import WIKI_DIRS, get_config
from .indexer import normalize_key

_cfg = get_config()
KB_ROOT = _cfg.kb_root
DATA_DIR = _cfg.data_dir
DELETIONS_PATH = DATA_DIR / "deletions.json"
INDEX_JSON = _cfg.index_path
LOG_MD = KB_ROOT / "wiki" / "log.md"
CONTENT_DIRS = _cfg.content_dirs
try:
    DATA_DIR_RELPREFIX = (DATA_DIR.relative_to(KB_ROOT).as_posix().rstrip("/") + "/")
except ValueError:  # 数据目录被指到 vault 外：幻影清理无从排除，退回默认名
    DATA_DIR_RELPREFIX = ".libry/"
BRANCH = os.environ.get("KB_GIT_BRANCH", "main")

WIKILINK_RE = re.compile(r"\[\[\s*([^\[\]|]+?)\s*(?:\|([^\[\]]+))?\]\]")
INDEX_LINE_RE = re.compile(r"^-\s*\[\[([^\[\]]+)\]\]\s*—\s*(.+?)\s*$")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    """本地日期（wiki/log.md 条目惯例用本地日期，与既有 log 条目一致）。"""
    return datetime.now().date().isoformat()


def _node() -> str:
    return os.environ.get("KB_ROLE") or os.uname().nodename


# ---------------- git ----------------

def _git_env():
    env = os.environ.copy()
    key = os.environ.get("KB_DEPLOY_KEY", "").strip()
    key_path = Path(key).expanduser() if key else Path.home() / ".ssh" / "id_ed25519_libry"
    if key_path.exists():
        env["GIT_SSH_COMMAND"] = f"ssh -i {key_path} -o IdentitiesOnly=yes"
    return env


def _git(*args):
    return subprocess.run(["git", *args], cwd=str(KB_ROOT),
                          capture_output=True, text=True, env=_git_env())


def _tracked_in_head(rel: str) -> bool:
    r = _git("ls-tree", "HEAD", "--", rel)
    return bool(r.stdout.strip())


# ---------------- deletions.json ----------------

def load_deletions() -> dict:
    if not DELETIONS_PATH.exists():
        return {}
    try:
        data = json.loads(DELETIONS_PATH.read_text(encoding="utf-8"))
        return data.get("files") or {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_deletions(files: dict):
    tmp = DELETIONS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps({"files": files}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(DELETIONS_PATH)


def _is_pending(e: dict) -> bool:
    return isinstance(e, dict) and e.get("marked_at") and not e.get("deleted") and not e.get("purged")


# ---------------- 路径守卫与标题解析 ----------------

def _content_dirs_for(kb_root: Path) -> list:
    """按给定 vault 根现场读取 content_dirs（不依赖导入时缓存的 config）。"""
    try:
        import tomllib
        with open(kb_root / "libry.toml", "rb") as fh:
            dirs = tomllib.load(fh).get("content_dirs") or []
    except Exception:
        return []
    if isinstance(dirs, str):
        dirs = [dirs]
    return [str(d).strip("/") for d in dirs if str(d).strip("/")]


def _allowed_rel(path: Path, content_dirs=None) -> bool:
    """rel 路径（POSIX 字符串）是否属于可删除范围。"""
    cds = CONTENT_DIRS if content_dirs is None else content_dirs
    parts = path.parts
    if not parts:
        return False
    if parts[0] == "wiki":
        return len(parts) == 3 and parts[1] in WIKI_DIRS
    return parts[0] in cds


def resolve_target(file: str, kb_root: Path = None):
    """返回 (abs_path, error)。error 非空则不可删。"""
    kb_root = kb_root or KB_ROOT
    rel = Path(file)
    if rel.is_absolute() or ".." in rel.parts:
        return None, "非法路径"
    abs_path = (kb_root / rel).resolve()
    try:
        abs_path.relative_to(kb_root)
    except ValueError:
        return None, "路径越出 KB_ROOT"
    if abs_path.suffix != ".md":
        return None, "仅支持 .md"
    if not _allowed_rel(Path(file), _content_dirs_for(kb_root)):
        return None, "不在可删除目录范围"
    return abs_path, ""


def _title_index() -> dict:
    if not INDEX_JSON.exists():
        return {}
    try:
        data = json.loads(INDEX_JSON.read_text(encoding="utf-8"))
        return {d["file"]: d.get("title") or "" for d in data.get("docs", [])}
    except (json.JSONDecodeError, OSError):
        return {}


def resolve_title(file: str, entry: dict, titles: dict) -> str:
    if entry.get("title"):
        return entry["title"]
    if titles.get(file):
        return titles[file]
    abs_path, err = resolve_target(file)
    if abs_path and abs_path.exists():
        try:
            m = H1_RE.search(abs_path.read_text(encoding="utf-8"))
            if m:
                return m.group(1).strip()
        except OSError:
            pass
    return Path(file).stem


# ---------------- 引用清理 ----------------

def _clean_sources_block(lines, basename, rel_posix):
    """处理一个文件 frontmatter 中的 sources 数组，返回 (新行列表, 移除数)。
    兼容 inline（sources: [a.md, "b.md"]）与 block list（sources:\\n  - a.md）两种写法。"""
    out = []
    removed = 0
    in_sources = False
    for line in lines:
        m_inline = re.match(r"^(\s*sources\s*:\s*)\[(.*)\]\s*$", line)
        if m_inline:
            items = [i.strip().strip("'\"") for i in m_inline.group(2).split(",")]
            kept = []
            for it in items:
                if it and it in (basename, rel_posix):
                    removed += 1
                elif it:
                    kept.append(it)
            line = m_inline.group(1) + "[" + ", ".join(kept) + "]"
            in_sources = False
            out.append(line)
            continue
        if re.match(r"^\s*sources\s*:\s*$", line):
            in_sources = True
            out.append(line)
            continue
        if in_sources:
            m_item = re.match(r"^(\s*-\s*)(['\"]?)(.*?)\2\s*$", line)
            if m_item:
                if m_item.group(3) in (basename, rel_posix):
                    removed += 1
                    continue  # 丢弃该条目
                out.append(line)
                continue
            in_sources = False  # 遇到非列表行，sources 块结束
        out.append(line)
    return out, removed


def clean_referencing_file(path: Path, targets: list, kb_root: Path = None) -> int:
    """清理单个文件对 targets（[(title, stem, basename, rel)]）的引用，返回改动处数。
    wikilink 命中规则：normalize_key(target) 命中 title 或 stem 的归一化键。"""
    kb_root = kb_root or KB_ROOT
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return 0
    changes = 0
    norm_map = {}
    for title, stem, basename, rel in targets:
        norm_map.setdefault(normalize_key(title), (title, basename, rel))
        norm_map.setdefault(normalize_key(stem), (title, basename, rel))

    # index.md：先在原文上删除整条索引行（wikilink 替换会把 [[...]] 剥掉，顺序不能反）
    if path.name == "index.md" and path.parent == kb_root:
        kept_lines = []
        for line in text.splitlines():
            m = INDEX_LINE_RE.match(line.strip())
            if m and normalize_key(m.group(1).strip()) in norm_map:
                changes += 1
                continue
            kept_lines.append(line)
        new_text = "\n".join(kept_lines) + ("\n" if text.endswith("\n") else "")
    else:
        new_text = text

    def repl(m):
        nonlocal changes
        target = m.group(1).strip()
        hit = norm_map.get(normalize_key(target))
        if not hit:
            return m.group(0)
        changes += 1
        alias = (m.group(2) or "").strip()
        return alias or target  # 纯文本替换，保句子通顺

    new_text = WIKILINK_RE.sub(repl, new_text)

    # frontmatter sources 数组
    fm = FRONTMATTER_RE.match(new_text)
    if fm:
        lines, removed = _clean_sources_block(fm.group(1).splitlines(),
                                              targets[0][2], targets[0][3])
        for title, stem, basename, rel in targets[1:]:
            lines, r2 = _clean_sources_block(lines, basename, rel)
            removed += r2
        if removed:
            changes += removed
            new_text = "---\n" + "\n".join(lines) + "\n---\n" + new_text[fm.end():]

    if changes and new_text != text:
        path.write_text(new_text, encoding="utf-8")
    return changes


def _scan_files():
    """所有可能被引用的 markdown：wiki/**、content_dirs/**、顶层 *.md（log.md 除外）。"""
    files = []
    wiki_dir = KB_ROOT / "wiki"
    if wiki_dir.is_dir():
        files += [p for p in wiki_dir.rglob("*.md") if p.name != "log.md"]
    for d in CONTENT_DIRS:
        dd = KB_ROOT / d
        if dd.is_dir():
            files += list(dd.rglob("*.md"))
    files += [p for p in KB_ROOT.glob("*.md")]
    return files


# ---------------- reconcile ----------------

def reconcile(files: dict, dry_run: bool) -> list:
    """清理 purged 终态条目的本机残留。返回处理了的 file 列表。

    残留的精确特征：文件在磁盘上、在索引中（reset --soft 保留了旧索引）、
    但不在 HEAD（远端删除提交已生效）。「不在索引」的同名文件是删除后有意
    重建、尚未提交的新页面，绝不能动。
    """
    done = []
    for f, e in sorted(files.items()):
        if not (isinstance(e, dict) and e.get("purged")):
            continue
        abs_path, err = resolve_target(f)
        if err or not abs_path.exists():
            continue
        if _tracked_in_head(f):
            continue  # 仍在 HEAD：删除提交尚未到达本机，或有意重建，跳过
        in_index = _git("ls-files", "--error-unmatch", "--", f).returncode == 0
        if not in_index:
            continue  # 未暂存的新文件（如重建的同名页面），不是残留
        done.append(f)
        if dry_run:
            continue
        try:
            abs_path.unlink()
        except OSError:
            pass
        _git("rm", "--cached", "--ignore-unmatch", "--", f)
    return done


def reconcile_phantoms(dry_run: bool) -> list:
    """清理「幻影改动」：sync_data 的 reset --soft 让 HEAD 跨过远端内容提交
    （如对端 purge 对引用页面的清理）后，索引/工作区仍停留在旧内容，相对新 HEAD
    呈现为「已暂存的本地修改」。若不清掉，本机的 publish 会把旧内容
    当成新改动重新提交，回滚远端的清理。

    幻影的精确特征：worktree == index（无真实本地编辑）但 index != HEAD。
    仅处理 HEAD 中仍存在的文件（checkout 对齐）；「在索引中但不在 HEAD」的
    暂存新文件可能是本机有意的新工作，不动（远端删除的页面由 reconcile() 按
    purged 标记单独处理）。运行数据目录下的同步文件由 sync_data 语义合并管理，不动。
    返回对齐了的 file 列表。
    """
    r = _git("diff", "--cached", "--name-only", "HEAD")
    if r.returncode != 0:
        return []
    done = []
    for f in r.stdout.splitlines():
        f = f.strip()
        if not f or f.startswith(DATA_DIR_RELPREFIX):
            continue
        if _git("diff", "--quiet", "--", f).returncode != 0:
            continue  # worktree != index：真实本地未暂存编辑，保留
        if not _tracked_in_head(f):
            continue  # 暂存的新文件（非幻影修改），保留
        done.append(f)
        if not dry_run:
            _git("checkout", "HEAD", "--", f)
    return done


# ---------------- 主流程 ----------------

def run(mode_dry_run=False, reconcile_only=False, do_commit=False, do_push=False) -> dict:
    report = {"node": _node(), "dry_run": mode_dry_run, "reconciled": [],
              "phantoms": [], "deleted": [], "skipped": [], "refs_cleaned": {},
              "log_appended": False, "committed": False, "pushed": False}
    files = load_deletions()

    report["reconciled"] = reconcile(files, mode_dry_run)
    report["phantoms"] = reconcile_phantoms(mode_dry_run)
    if reconcile_only:
        return report

    pending = {f: e for f, e in files.items() if _is_pending(e)}
    if not pending:
        return report

    titles = _title_index()
    targets = []          # (title, stem, basename, rel)
    touched = set()       # 变更/删除的内容路径（git add 用）
    for f, e in sorted(pending.items()):
        abs_path, err = resolve_target(f)
        if err:
            report["skipped"].append({"file": f, "reason": err})
            continue
        title = resolve_title(f, e, titles)
        stem = Path(f).stem
        targets.append((title, stem, Path(f).name, f))
        if not abs_path.exists():
            # 文件已不在（可能已被手工删除）：直接转 purged
            report["deleted"].append({"file": f, "title": title, "note": "文件已不存在"})
            continue
        if mode_dry_run:
            report["deleted"].append({"file": f, "title": title})
            touched.add(f)
            continue
        try:
            abs_path.unlink()
            report["deleted"].append({"file": f, "title": title})
            touched.add(f)
        except OSError as ex:
            report["skipped"].append({"file": f, "reason": f"删除失败: {ex}"})
            continue

    # 实际删除（或已不存在）的文件才进入 purged 终态与日志
    purged_files = [d["file"] for d in report["deleted"]]
    # targets 只保留真正删除成功的（被删失败的文件仍要保留其引用）
    failed = {s["file"] for s in report["skipped"]}
    targets = [t for t in targets if t[3] not in failed]

    if targets:
        for path in _scan_files():
            rel = path.relative_to(KB_ROOT).as_posix()
            if any(rel == t[3] for t in targets):
                continue  # 被删文件自身
            if mode_dry_run:
                # dry-run：读内容统计命中但不写盘
                n = _count_hits(path, targets)
            else:
                n = clean_referencing_file(path, targets)
            if n:
                report["refs_cleaned"][rel] = n
                touched.add(rel)

        # log.md 追加（dry-run 不写）
        deleted_real = [d for d in report["deleted"] if not d.get("note")]
        if deleted_real:
            report["log_appended"] = True
            if not mode_dry_run and LOG_MD.parent.is_dir():
                lines = [f"## [{_today()}] purge | 删除 {len(deleted_real)} 个待删除页面",
                         f"由 Web 待删除标记触发，libry purge 执行于 {report['node']}。"]
                for d in deleted_real:
                    lines.append(f"- {d['title']}（{d['file']}）")
                lines.append(f"引用清理共 {sum(report['refs_cleaned'].values())} 处，"
                             f"涉及 {len(report['refs_cleaned'])} 个文件。")
                with open(LOG_MD, "a", encoding="utf-8") as fh:
                    fh.write("\n" + "\n".join(lines) + "\n")
                touched.add("wiki/log.md")

        if not mode_dry_run:
            # 暂存内容变更（不含 deletions.json —— 由 sync_data 专门提交）。
            # pathspec 必须命中：磁盘存在，或已删除但仍被 git 跟踪（暂存删除）；
            # 从未入库且已删除的文件（无跟踪记录）跳过，否则整个 git add 会报错。
            stageable = []
            for p in sorted(touched):
                if (KB_ROOT / p).exists():
                    stageable.append(p)
                elif _git("ls-files", "--error-unmatch", "--", p).returncode == 0:
                    stageable.append(p)
            if stageable:
                _git("add", "-A", "--", *stageable)

    if do_commit and not mode_dry_run and purged_files:
        r = _git("diff", "--cached", "--quiet")
        if r.returncode != 0:
            msg = f"purge: {_today()} 删除 {len(purged_files)} 个待删除页面"
            cr = _git("commit", "-m", msg)
            report["committed"] = cr.returncode == 0
            if not report["committed"]:
                report["commit_error"] = (cr.stderr or cr.stdout).strip()[:300]
    if do_push and report.get("committed") and not mode_dry_run:
        for _attempt in range(3):
            pr = _git("push", "origin", BRANCH)
            if pr.returncode == 0:
                report["pushed"] = True
                break
            _git("fetch", "origin", BRANCH)
            rr = _git("rebase", f"origin/{BRANCH}")
            if rr.returncode != 0:
                _git("rebase", "--abort")
                report["push_error"] = (rr.stderr or rr.stdout).strip()[:300]
                break
        if not report["pushed"] and "push_error" not in report:
            report["push_error"] = "push 重试 3 次仍失败"
        # push 失败则不写 purged 终态（标记保持 pending，下次执行重试），
        # 避免对端先收到 purged 标记却从未收到内容删除提交。
        if not report["pushed"]:
            return report

    if purged_files and not mode_dry_run:
        # 条目转 purged 终态
        ts = _now()
        for f in purged_files:
            files[f] = {"purged": ts, "purged_by": report["node"]}
        save_deletions(files)

    return report


def _count_hits(path: Path, targets: list) -> int:
    """dry-run 用：只读统计会命中的引用处数（wikilink + index 行 + sources 项）。"""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return 0
    norm_keys = set()
    for title, stem, basename, rel in targets:
        norm_keys.add(normalize_key(title))
        norm_keys.add(normalize_key(stem))
    n = 0
    for m in WIKILINK_RE.finditer(text):
        if normalize_key(m.group(1).strip()) in norm_keys:
            n += 1
    if path.name == "index.md" and path.parent == KB_ROOT:
        for line in text.splitlines():
            m = INDEX_LINE_RE.match(line.strip())
            if m and normalize_key(m.group(1).strip()) in norm_keys:
                n += 1
    fm = FRONTMATTER_RE.match(text)
    if fm:
        for title, stem, basename, rel in targets:
            _lines, removed = _clean_sources_block(fm.group(1).splitlines(), basename, rel)
            n += removed
    return n


def main() -> int:
    args = set(sys.argv[1:])
    dry = "--dry-run" in args
    report = run(mode_dry_run=dry,
                 reconcile_only="--reconcile-only" in args,
                 do_commit="--commit" in args,
                 do_push="--push" in args)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
