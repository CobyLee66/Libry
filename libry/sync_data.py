#!/usr/bin/env python3
"""跨端用户数据同步：本地磁盘 <-> git origin，双向合并。

同步范围（仅这五个文件，绝不触碰代码/文档）：
  <data>/users.json       账户（bcrypt 哈希 + 墓碑）
  <data>/state.json       已读/新增水位 + 阅读进度（progress）+ 手动书签（marks）
  <data>/bookmarks.json   收藏夹（updated_at + 墓碑）
  <data>/visibility.json  文档个人/共享可见性覆盖（updated_at LWW）
  <data>/deletions.json   待删除标记（marked_at/deleted/purged LWW）

合并语义：CRDT 风格的「最后写入胜（LWW）+ 删除墓碑」，满足交换律/结合律/幂等律，
因此双向合并无需三方 base、不会产生 git 冲突。时间戳统一解析为 UTC datetime 比较。

流程：fetch -> 语义合并写回磁盘 -> 通知本机进程热重载 -> 提交(仅数据文件) -> push，
非 fast-forward 时回到 fetch 重试（最多 3 次）。带 flock 锁防止并发。

前置条件：vault 本身是 git 仓库（多机模式），数据目录（默认 .libry/）位于 vault 内。
环境变量：KB_DEPLOY_KEY（可选的写权限部署密钥）、KB_LOCAL_URL（默认
http://127.0.0.1:8000）、KB_GIT_BRANCH（默认 main）、SYNC_SECRET。

用法：
    libry sync-data [--dry-run]   或   python -m libry.sync_data [--dry-run]
"""
import fcntl
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .config import get_config

_cfg = get_config()
KB_ROOT = _cfg.kb_root
DATA_DIR = _cfg.data_dir
BRANCH = os.environ.get("KB_GIT_BRANCH", "main")
LOCAL_URL = os.environ.get("KB_LOCAL_URL", "http://127.0.0.1:8000").rstrip("/")

# (文件名, 相对 vault 根的路径, 合并函数) —— 路径按数据目录实际位置计算
FILES = []  # 下方填充（合并函数定义后）
SYNC_STATUS_PATH = DATA_DIR / "sync-status.json"
LOCK_PATH = DATA_DIR / "sync.lock"
COMMIT_PREFIX = "sync: 用户数据"


# ---------------- 时间戳 ----------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _cmp_ts(a, b) -> int:
    """比较两个 ISO 时间戳：a 较晚返回正数，相等 0，较早负数；None 视为最旧。"""
    da, db = _parse_ts(a), _parse_ts(b)
    if da is None and db is None:
        return 0
    if da is None:
        return -1
    if db is None:
        return 1
    return (da > db) - (da < db)


def _max_ts(a, b):
    return a if _cmp_ts(a, b) >= 0 else b


# ---------------- 合并函数（纯函数，可直接单测） ----------------

def _pick(lhs, rhs, l_ts, r_ts):
    """按时间戳取较新者，平局取远端 rhs（确定性）。"""
    return lhs if _cmp_ts(l_ts, r_ts) > 0 else rhs


def merge_users(local, remote):
    """users.json：并集 + LWW(updated_at/deleted) + 保留墓碑。"""
    lu = (local or {}).get("users") or {}
    ru = (remote or {}).get("users") or {}
    out = {}
    for name in set(lu) | set(ru):
        lhs, rhs = lu.get(name), ru.get(name)
        if lhs is None:
            out[name] = rhs
        elif rhs is None:
            out[name] = lhs
        else:
            out[name] = _pick(lhs, rhs,
                              lhs.get("updated_at") or lhs.get("deleted"),
                              rhs.get("updated_at") or rhs.get("deleted"))
    return {"users": out}


def merge_bookmarks(local, remote):
    """bookmarks.json：按用户/文件并集 + LWW(updated_at/deleted) + 保留墓碑。"""
    lu = (local or {}).get("users") or {}
    ru = (remote or {}).get("users") or {}
    out = {}
    for name in set(lu) | set(ru):
        lb = lu.get(name) or {}
        rb = ru.get(name) or {}
        merged = {}
        for f in set(lb) | set(rb):
            lhs, rhs = lb.get(f), rb.get(f)
            if lhs is None:
                merged[f] = rhs
            elif rhs is None:
                merged[f] = lhs
            else:
                merged[f] = _pick(lhs, rhs,
                                  lhs.get("updated_at") or lhs.get("added") or lhs.get("deleted"),
                                  rhs.get("updated_at") or rhs.get("added") or rhs.get("deleted"))
        out[name] = merged
    return {"users": out}


def _merge_pos_map(lhs, rhs):
    """progress/marks 位置表的 per-file LWW 合并：updated_at/deleted 较新者胜，
    平局取远端（确定性，与 _pick 一致）；墓碑条目照常参与比较（删除可后胜）。"""
    lhs, rhs = lhs or {}, rhs or {}
    out = {}
    for f in set(lhs) | set(rhs):
        a, b = lhs.get(f), rhs.get(f)
        if a is None:
            out[f] = b
        elif b is None:
            out[f] = a
        else:
            out[f] = _pick(a, b,
                           a.get("updated_at") or a.get("deleted"),
                           b.get("updated_at") or b.get("deleted"))
    return out


def merge_state(local, remote):
    """state.json：read 单调并集（取更晚时间戳），水位取最大；
    progress per-file LWW(updated_at)；marks per-file LWW(updated_at/deleted) 保留墓碑。"""
    lu = (local or {}).get("users") or {}
    ru = (remote or {}).get("users") or {}
    out = {}
    for name in set(lu) | set(ru):
        lhs = lu.get(name) or {}
        rhs = ru.get(name) or {}
        lr, rr = lhs.get("read") or {}, rhs.get("read") or {}
        mread = {}
        for f in set(lr) | set(rr):
            a, b = lr.get(f), rr.get(f)
            if a is None:
                mread[f] = b
            elif b is None:
                mread[f] = a
            else:
                mread[f] = a if _cmp_ts(a, b) > 0 else b
        out[name] = {
            "read": mread,
            "new_since": _max_ts(lhs.get("new_since"), rhs.get("new_since")),
            "pending_since": _max_ts(lhs.get("pending_since"), rhs.get("pending_since")),
            "progress": _merge_pos_map(lhs.get("progress"), rhs.get("progress")),
            "marks": _merge_pos_map(lhs.get("marks"), rhs.get("marks")),
        }
    return {"users": out}


def merge_visibility(local, remote):
    """visibility.json：按文件并集 + LWW(updated_at)。
    每次切换都是显式写入（含切回 shared），无需删除墓碑。"""
    lf = (local or {}).get("files") or {}
    rf = (remote or {}).get("files") or {}
    out = {}
    for f in set(lf) | set(rf):
        lhs, rhs = lf.get(f), rf.get(f)
        if lhs is None:
            out[f] = rhs
        elif rhs is None:
            out[f] = lhs
        else:
            out[f] = _pick(lhs, rhs, lhs.get("updated_at"), rhs.get("updated_at"))
    return {"files": out}


def merge_deletions(local, remote):
    """deletions.json：按文件并集 + LWW（marked_at/deleted/purged 取最新）。
    三种状态都显式写入（标记/取消墓碑/清理终态），无需额外墓碑。"""
    lf = (local or {}).get("files") or {}
    rf = (remote or {}).get("files") or {}
    out = {}
    for f in set(lf) | set(rf):
        lhs, rhs = lf.get(f), rf.get(f)
        if lhs is None:
            out[f] = rhs
        elif rhs is None:
            out[f] = lhs
        else:
            l_ts = lhs.get("purged") or lhs.get("deleted") or lhs.get("marked_at")
            r_ts = rhs.get("purged") or rhs.get("deleted") or rhs.get("marked_at")
            out[f] = _pick(lhs, rhs, l_ts, r_ts)
    return {"files": out}


def _files_spec():
    """[(名称, vault 相对路径, 合并函数)]；数据目录在 vault 外时报错。"""
    return [
        ("users.json", _cfg.data_rel("users.json"), merge_users),
        ("state.json", _cfg.data_rel("state.json"), merge_state),
        ("bookmarks.json", _cfg.data_rel("bookmarks.json"), merge_bookmarks),
        ("visibility.json", _cfg.data_rel("visibility.json"), merge_visibility),
        ("deletions.json", _cfg.data_rel("deletions.json"), merge_deletions),
    ]


FILES = _files_spec()


# ---------------- git / 文件 IO ----------------

def _git_env():
    env = os.environ.copy()
    key = os.environ.get("KB_DEPLOY_KEY", "").strip()
    key_path = Path(key).expanduser() if key else Path.home() / ".ssh" / "id_ed25519_libry"
    if key_path.exists():
        # 专用「写权限」部署密钥，仅用于本模块的 git 操作（代码拉取仍用默认密钥）
        env["GIT_SSH_COMMAND"] = f"ssh -i {key_path} -o IdentitiesOnly=yes"
    return env


def _git(*args, env=None):
    return subprocess.run(["git", *args], cwd=str(KB_ROOT),
                          capture_output=True, text=True, env=env or _git_env())


def _read_local(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _read_remote(rel: str, env):
    r = _git("show", f"origin/{BRANCH}:{rel}", env=env)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None


def _write_local(path: Path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    if path.name in ("users.json", "bookmarks.json", "visibility.json", "deletions.json"):
        os.chmod(tmp, 0o600)
    tmp.replace(path)


def _write_status(result: str, detail: str = ""):
    try:
        SYNC_STATUS_PATH.write_text(
            json.dumps({"last_run": _now(), "result": result, "detail": detail},
                       ensure_ascii=False, indent=1),
            encoding="utf-8")
    except OSError:
        pass


def _reload_app():
    """通知本机 Web 进程热重载内存中的 state/bookmarks（失败不阻断）。"""
    secret = os.environ.get("SYNC_SECRET", "")
    if not secret:
        return
    req = urllib.request.Request(f"{LOCAL_URL}/api/sync-data/reload", method="POST",
                                 headers={"X-Sync-Secret": secret})
    try:
        urllib.request.urlopen(req, timeout=8)
    except Exception:
        pass


def _reconcile_purged() -> bool:
    """清理远端 purge 后本机磁盘的残留文件（best-effort，失败不阻断同步）。

    场景：对端执行 purge 并 push 内容删除后，本机 reset --soft 到 origin 时
    工作区/索引不更新，被删文件会残留在磁盘（且索引里呈 staged-new）。若不清掉，
    下次 publish 的 git add 会把它们重新提交（复活）。
    返回是否有文件被清理（有则需要让本机 Web 进程重建索引，否则已删页面仍在列表残留）。
    """
    try:
        r = subprocess.run([sys.executable, "-m", "libry.purge_marked", "--reconcile-only"],
                           cwd=str(KB_ROOT), timeout=60, capture_output=True, text=True)
        report = json.loads(r.stdout) if r.stdout else {}
        return bool(report.get("reconciled")) or bool(report.get("phantoms"))
    except Exception:
        return False


def _reindex_app():
    """通知本机 Web 进程重建索引并热重载（reconcile 清掉残留文件后调用；失败不阻断）。"""
    secret = os.environ.get("SYNC_SECRET", "")
    if not secret:
        return
    req = urllib.request.Request(f"{LOCAL_URL}/api/reindex", method="POST",
                                 headers={"X-Sync-Secret": secret})
    try:
        urllib.request.urlopen(req, timeout=60)
    except Exception:
        pass


def _merge_all(env):
    """合并五个文件写回磁盘；返回是否有本地磁盘变化。"""
    changed = False
    for name, rel, merger in FILES:
        local = _read_local(DATA_DIR / name)
        remote = _read_remote(rel, env)
        merged = merger(local, remote)
        if merged != local:
            _write_local(DATA_DIR / name, merged)
            changed = True
    return changed


def _ahead_commits_are_data(env) -> bool:
    """本地领先 origin 的提交是否全部为本模块的数据提交。"""
    r = _git("log", "--format=%s", f"origin/{BRANCH}..{BRANCH}", env=env)
    if r.returncode != 0:
        return True
    msgs = [m for m in r.stdout.splitlines() if m.strip()]
    return all(COMMIT_PREFIX in m for m in msgs)


def _push_merged(env, changed: bool, dry_run: bool):
    """提交（仅数据文件）并 push，非 ff 返回 False 以便上层重试。"""
    if dry_run:
        return "dry-run"
    # 丢弃可能存在的旧数据提交，把 HEAD 对齐 origin，但保留工作区（含未提交的代码改动）
    if not _ahead_commits_are_data(env):
        return "abort"
    paths = [rel for _, rel, _ in FILES if (KB_ROOT / rel).exists()]
    if not paths:
        return "no changes"
    _git("reset", "--soft", f"origin/{BRANCH}", env=env)
    _git("add", "--", *paths, env=env)
    r = _git("commit", "-m", f"{COMMIT_PREFIX} {_now()}", "--", *paths, env=env)
    if r.returncode != 0:
        if "nothing to commit" in (r.stdout or "") + (r.stderr or ""):
            return "no changes"
        raise RuntimeError(f"git commit 失败: {(r.stderr or r.stdout).strip()[:200]}")
    pr = _git("push", "origin", BRANCH, env=env)
    return "pushed" if pr.returncode == 0 else "retry"


def run(dry_run: bool = False) -> int:
    env = _git_env()
    lock = None
    try:
        lock = open(LOCK_PATH, "a+")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        _write_status("skipped", "another sync in progress")
        return 0

    try:
        result = "error"
        detail = ""
        try:
            for attempt in range(3):
                r = _git("fetch", "origin", BRANCH, env=env)
                if r.returncode != 0:
                    result, detail = "error", f"git fetch 失败: {r.stderr.strip()[:200]}"
                    break
                changed = _merge_all(env)
                if changed:
                    _reload_app()
                pr = _push_merged(env, changed, dry_run)
                if pr in ("pushed", "no changes", "dry-run"):
                    result = pr
                    break
                if pr == "abort":
                    result, detail = "error", "本地有未推送的非数据提交，已跳过"
                    break
                # pr == "retry"：远端前进，回到 fetch 重新合并
                result, detail = "error", "push 冲突，重试后仍未成功"
            # HEAD 已对齐 origin（_push_merged 的 reset --soft）后，
            # 清理远端 purge 在本机留下的已删文件残留（防后续 publish 复活）；
            # 确有清理时让本机 Web 进程重建索引，避免已删页面在列表中残留
            if not dry_run and _reconcile_purged():
                _reindex_app()
        except Exception as e:
            result, detail = "error", str(e)[:200]
        _write_status(result, detail)
        print(f"[sync-data] {result} {detail}".strip())
        return 0 if result in ("pushed", "no changes", "dry-run", "skipped") else 1
    finally:
        if lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_UN)
                lock.close()
            except OSError:
                pass


if __name__ == "__main__":
    sys.exit(run(dry_run="--dry-run" in sys.argv))
