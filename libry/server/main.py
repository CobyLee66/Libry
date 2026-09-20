"""Libry（书阁）知识库 Web 浏览应用 — FastAPI 入口。

启动：
    libry serve                       # vault 根目录或 KB_ROOT 指定的知识库
    uvicorn libry.server.main:app --host 127.0.0.1 --port 8000
"""
import atexit
import json
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .. import indexer
from ..config import get_config
from .auth import Auth, RateLimiter, make_admin_dependency, make_session_dependency
from .bookmarks import BookmarkStore
from .deletions import DeletionStore
from .render import build_link_map, render_document
from .state import StateStore
from .visibility import VisibilityStore

_cfg = get_config()
KB_ROOT = _cfg.kb_root
DATA_DIR = _cfg.data_dir
INDEX_PATH = _cfg.index_path
GRAPH_PATH = _cfg.graph_path
STATE_PATH = DATA_DIR / "state.json"
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
# 多机同步脚本随引擎仓库分发（pip 安装缺失时相关端点自动降级）
ENGINE_ROOT = Path(__file__).resolve().parents[2]
SYNC_SCRIPT = ENGINE_ROOT / "deploy" / "sync.sh"
SYNC_STATUS_PATH = DATA_DIR / "sync-status.json"
SYNC_SECRET = os.environ.get("SYNC_SECRET", "")

DOC_TYPES = ["sources", "entities", "concepts", "synthesis", "archive"]
PAGE_SIZE_DEFAULT = 50

app = FastAPI(title="Libry KB Web", docs_url=None, redoc_url=None)

auth = Auth(
    users_path=DATA_DIR / "users.json",
    session_secret=os.environ.get("SESSION_SECRET", ""),
    cookie_secure=os.environ.get("KB_COOKIE_SECURE", "").lower() in ("1", "true", "yes"),
    bootstrap_hash=os.environ.get("KB_PASSWORD_HASH", ""),
    legacy_auth_path=DATA_DIR / "auth.json",
)
require_session = make_session_dependency(auth)
require_admin = make_admin_dependency(auth)
state = StateStore(STATE_PATH)
atexit.register(state.flush)  # 防抖落盘：进程退出时强制刷掉未写入的已读标记
bookmarks = BookmarkStore(DATA_DIR / "bookmarks.json")
visibility = VisibilityStore(DATA_DIR / "visibility.json")
deletions = DeletionStore(DATA_DIR / "deletions.json")
sync_limiter = RateLimiter(max_hits=10, window_sec=60)
data_sync_limiter = RateLimiter(max_hits=3, window_sec=60)
purge_limiter = RateLimiter(max_hits=3, window_sec=60)


def client_ip(request: Request) -> str:
    """限速用客户端 IP：仅当直连方是本机反代（Caddy 等）时才采纳 X-Forwarded-For 首跳。"""
    direct = request.client.host if request.client else "unknown"
    if direct in ("127.0.0.1", "::1"):
        xff = request.headers.get("X-Forwarded-For", "")
        if xff:
            return xff.split(",")[0].strip()
    return direct


_index_lock = threading.Lock()
_index = {"docs": [], "tag_groups": {}, "standard_tags": []}
_link_map = {}
_doc_map = {}
_graph = {"related": {}, "edges": []}


def load_index():
    """加载 index.json（及可选的 graph.json）到内存；index.json 不存在则现场重建。"""
    global _index, _link_map, _doc_map, _graph
    if not INDEX_PATH.exists():
        indexer.build_index(str(KB_ROOT))
    with _index_lock:
        _index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        _link_map = build_link_map(_index["docs"])
        _doc_map = {d["file"]: d for d in _index["docs"]}
        if GRAPH_PATH.exists():
            try:
                _graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                _graph = {"related": {}, "edges": []}
        else:
            _graph = {"related": {}, "edges": []}


def get_docs():
    with _index_lock:
        return _index


def get_graph():
    with _index_lock:
        return _graph


def doc_by_file(file: str):
    with _index_lock:
        return _doc_map.get(file)


def vis_state(d: dict) -> tuple:
    """文档生效的 (visibility, owner)：运行时覆盖层优先，否则用 frontmatter 初始值。"""
    ov = visibility.get(d["file"])
    if ov:
        return ov["visibility"], ov.get("owner", "")
    return d.get("visibility") or "shared", d.get("owner") or ""


def can_see(user: str, d: dict) -> bool:
    """共享文档人人可见；个人文档仅所有者与管理员可见。"""
    v, owner = vis_state(d)
    return v == "shared" or owner == user or auth.is_admin(user)


def user_context(user: str) -> dict:
    """请求级用户状态快照：已读/收藏集合与新增水位各取一次。

    列表页逐条构造 public_doc 时复用，避免每条都全量复制集合。
    """
    return {
        "read_set": state.read_set(user),
        "bookmark_set": bookmarks.bookmark_set(user),
        "deletion_set": deletions.marked_set(),
        "since": state.new_since_date(user),
    }


def public_doc(d: dict, user: str, ctx: dict = None) -> dict:
    """去掉 content 语料，附加 read/is_new/bookmarked/可见性状态。

    ctx 传 user_context() 快照可避免列表页逐条复制集合；缺省时现场取一次。
    """
    c = ctx or user_context(user)
    out = {k: v for k, v in d.items() if k != "content"}
    out["read"] = d["file"] in c["read_set"]
    # 与 StateStore.is_new 同语义：已读或无 created 不算新增
    out["is_new"] = (bool(c["since"]) and bool(d["created"])
                     and not out["read"] and d["created"] > c["since"])
    out["bookmarked"] = d["file"] in c["bookmark_set"]
    out["marked_deleted"] = d["file"] in c["deletion_set"]
    out["visibility"], out["owner"] = vis_state(d)
    out["can_toggle"] = can_see(user, d)
    return out


def filter_docs(q, tags, type_, date_from, date_to, user, visibility_filter=""):
    docs = get_docs()["docs"]
    q = (q or "").strip().lower()
    tag_list = [t for t in (tags or "").split(",") if t]
    vis_filter = (visibility_filter or "").strip().lower()
    result = []
    for d in docs:
        if not can_see(user, d):
            continue
        if vis_filter in ("shared", "personal") and vis_state(d)[0] != vis_filter:
            continue
        if type_ and d["type"] != type_:
            continue
        if date_from and (not d["created"] or d["created"] < date_from):
            continue
        if date_to and (not d["created"] or d["created"] > date_to):
            continue
        if tag_list and not all(t in d["tags"] for t in tag_list):
            continue
        if q and q not in d["title"].lower() and q not in d["summary"].lower():
            continue
        result.append(d)
    return result


def status_of(d, read_set, since):
    is_read = d["file"] in read_set
    is_new = bool(since) and bool(d["created"]) and d["created"] > since and not is_read
    return is_read, is_new


# ---------------- 认证 ----------------

@app.post("/api/login")
async def login(request: Request, response: Response):
    ip = client_ip(request)
    if not auth.login_limiter.allow(ip):
        raise HTTPException(status_code=429, detail="尝试过于频繁，请稍后再试")
    body = await request.json()
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", ""))
    if not auth.verify(username, password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    auth.issue_session(response, username)
    state.on_login(username)
    return {"ok": True, "username": username, "admin": auth.is_admin(username)}


@app.post("/api/logout")
async def logout(response: Response):
    auth.clear_session(response)
    return {"ok": True}


@app.get("/api/session")
async def session_status(request: Request):
    user = auth.current_user(request)
    return {
        "authenticated": user is not None,
        "username": user,
        "admin": auth.is_admin(user) if user else False,
    }


@app.post("/api/password")
async def change_password(request: Request, user: str = Depends(require_session)):
    """设置页修改自己的密码：校验当前密码（限速），新哈希写入 users.json。"""
    ip = client_ip(request)
    if not auth.login_limiter.allow(ip):
        raise HTTPException(status_code=429, detail="尝试过于频繁，请稍后再试")
    body = await request.json()
    old_password = str(body.get("old_password", ""))
    new_password = str(body.get("new_password", ""))
    if not auth.verify(user, old_password):
        raise HTTPException(status_code=401, detail="当前密码错误")
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="新密码至少 8 位")
    auth.set_password(user, new_password)
    return {"ok": True}


# ---------------- 账户管理（管理员） ----------------

@app.get("/api/users")
async def list_users(admin: str = Depends(require_admin)):
    return {"users": auth.list_users()}


@app.post("/api/users")
async def create_user(request: Request, admin: str = Depends(require_admin)):
    body = await request.json()
    auth.add_user(str(body.get("username", "")), str(body.get("password", "")),
                  admin=bool(body.get("admin")))
    return {"ok": True, "users": auth.list_users()}


@app.delete("/api/users/{username}")
async def delete_user(username: str, admin: str = Depends(require_admin)):
    auth.delete_user(username, by_user=admin)
    return {"ok": True, "users": auth.list_users()}


# ---------------- 数据 ----------------

@app.get("/api/meta")
async def meta(user: str = Depends(require_session)):
    idx = get_docs()
    docs = [d for d in idx["docs"] if can_see(user, d)]
    read_set = state.read_set(user)
    since = state.new_since_date(user)
    unread = sum(1 for d in docs if d["file"] not in read_set)
    new = sum(1 for d in docs if status_of(d, read_set, since)[1])
    dates = sorted(d["created"] for d in docs if d["created"])
    return {
        "tag_groups": idx.get("tag_groups", {}),
        "standard_tags": idx.get("standard_tags", []),
        "types": DOC_TYPES,
        "date_range": {"min": dates[0] if dates else "", "max": dates[-1] if dates else ""},
        "stats": {"total": len(docs), "unread": unread, "new": new},
        "generated_at": idx.get("generated_at", ""),
    }


@app.get("/api/docs")
async def list_docs(q: str = "", tags: str = "", type: str = "",
                    date_from: str = "", date_to: str = "",
                    visibility: str = "",
                    status: str = "all", sort: str = "created",
                    order: str = "", page: int = 1, page_size: int = PAGE_SIZE_DEFAULT,
                    user: str = Depends(require_session)):
    filtered = filter_docs(q, tags, type, date_from, date_to, user, visibility)
    read_set = state.read_set(user)
    since = state.new_since_date(user)

    # 单遍统计 read/new，unread 用补集（status_of 保证 new ⊆ unread）
    n_read = n_new = 0
    for d in filtered:
        is_read, is_new = status_of(d, read_set, since)
        if is_read:
            n_read += 1
        elif is_new:
            n_new += 1
    counts = {
        "all": len(filtered),
        "new": n_new,
        "unread": len(filtered) - n_read,
        "read": n_read,
    }

    def matches_status(d, s):
        is_read, is_new = status_of(d, read_set, since)
        if s == "read":
            return is_read
        if s == "unread":
            return not is_read
        if s == "new":
            return is_new
        return True

    items = [d for d in filtered if matches_status(d, status)]

    if status == "read":
        # 已读 tab：按标记已读的时间倒序（近的在前），忽略 sort 选项
        read_ts = state.read_map(user)
        items.sort(key=lambda d: (read_ts.get(d["file"]) or "", d["title"]), reverse=True)
    elif sort == "title":
        items.sort(key=lambda d: d["title"])
        if order == "desc":
            items.reverse()
    else:
        key = "updated" if sort == "updated" else "created"
        items.sort(key=lambda d: (d[key] or "", d["title"]), reverse=(order != "asc"))

    page = max(1, page)
    page_size = min(max(1, page_size), 200)
    total = len(items)
    start = (page - 1) * page_size
    ctx = {"read_set": read_set, "bookmark_set": bookmarks.bookmark_set(user),
           "deletion_set": deletions.marked_set(), "since": since}
    return {
        "total": total, "page": page, "page_size": page_size,
        "counts": counts,
        "items": [public_doc(d, user, ctx) for d in items[start:start + page_size]],
    }


@app.get("/api/doc")
async def get_doc(file: str, user: str = Depends(require_session)):
    d = doc_by_file(file)
    if not d:
        raise HTTPException(status_code=404, detail="文档不存在")
    if not can_see(user, d):
        raise HTTPException(status_code=404, detail="文档不存在")  # 个人文档对无权者与不存在不可区分
    md_path = KB_ROOT / file
    if not md_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    html = render_document(md_path, _link_map, KB_ROOT, set(_doc_map))

    # 上一篇/下一篇：按 created 在当前用户可见的文档内排序
    ordered = sorted((x for x in get_docs()["docs"] if can_see(user, x)),
                     key=lambda x: (x["created"] or "", x["title"]))
    prev_doc = next_doc = None
    for i, x in enumerate(ordered):
        if x["file"] == file:
            if i > 0:
                prev_doc = {"file": ordered[i - 1]["file"], "title": ordered[i - 1]["title"]}
            if i < len(ordered) - 1:
                next_doc = {"file": ordered[i + 1]["file"], "title": ordered[i + 1]["title"]}
            break

    state.mark_read(user, [file])  # 打开即自动标记已读
    related = [
        {"file": r["file"], "score": r["score"],
         "title": (doc_by_file(r["file"]) or {}).get("title", r["file"]),
         "type": (doc_by_file(r["file"]) or {}).get("type", "")}
        for r in get_graph().get("related", {}).get(file, [])
        if doc_by_file(r["file"]) and can_see(user, doc_by_file(r["file"]))
    ]
    return {
        "html": html,
        "meta": public_doc(d, user),
        "prev": prev_doc,
        "next": next_doc,
        "bookmark_tags": bookmarks.get_tags(user, file),
        "related": related,
    }


# ---------------- 关联图 ----------------

def _graph_node(file: str) -> dict:
    d = doc_by_file(file) or {}
    return {"file": file, "title": d.get("title", file),
            "type": d.get("type", ""), "tags": d.get("tags", [])}


@app.get("/api/graph")
async def graph(file: str = "", user: str = Depends(require_session)):
    """关联图数据。带 file 返回以该文档为中心的一跳局部图；不带返回全库图。
    graph.json 未生成时返回空结构（前端自动隐藏图功能）。
    节点/边按当前用户可见性过滤——个人文档不进入他人的图。"""
    g = get_graph()

    def visible(f: str) -> bool:
        d = doc_by_file(f)
        return bool(d) and can_see(user, d)

    if file:
        if not doc_by_file(file):
            raise HTTPException(status_code=404, detail="文档不存在")
        if not visible(file):
            raise HTTPException(status_code=404, detail="文档不存在")
        neighbors = [r["file"] for r in g.get("related", {}).get(file, []) if visible(r["file"])]
        nodes = {file: _graph_node(file)}
        for f in neighbors:
            nodes[f] = _graph_node(f)
        in_sub = set(nodes)
        edges = [[a, b, w] for a, b, w in g.get("edges", [])
                 if a in in_sub and b in in_sub]
        # 中心到邻居的边不受全图 top-K 裁剪影响，按 related 分数补齐
        have = {tuple(sorted((a, b))) for a, b, _ in edges}
        for r in g.get("related", {}).get(file, []):
            if not visible(r["file"]):
                continue
            key = tuple(sorted((file, r["file"])))
            if key not in have:
                edges.append([file, r["file"], r["score"]])
        return {"nodes": list(nodes.values()), "edges": edges, "center": file}
    visible_files = {d["file"] for d in get_docs()["docs"] if can_see(user, d)}
    return {
        "nodes": [_graph_node(f) for f in visible_files],
        "edges": [[a, b, w] for a, b, w in g.get("edges", [])
                  if a in visible_files and b in visible_files],
        "generated_at": g.get("generated_at", ""),
    }


# ---------------- 状态 ----------------

async def _files_body(request: Request, user: str):
    body = await request.json()
    files = body.get("files") or []
    if not isinstance(files, list):
        raise HTTPException(status_code=400, detail="files 必须是数组")
    valid = {d["file"] for d in get_docs()["docs"] if can_see(user, d)}
    return [f for f in files if f in valid]


@app.post("/api/state/read")
async def mark_read(request: Request, user: str = Depends(require_session)):
    files = await _files_body(request, user)
    state.mark_read(user, files)
    return {"ok": True, "count": len(files)}


@app.post("/api/state/unread")
async def mark_unread(request: Request, user: str = Depends(require_session)):
    files = await _files_body(request, user)
    state.mark_unread(user, files)
    return {"ok": True, "count": len(files)}


@app.post("/api/state/ack-new")
async def ack_new(user: str = Depends(require_session)):
    state.ack_new(user)
    return {"ok": True}


# ---------------- 收藏夹 ----------------

def _valid_file(file: str, user: str):
    """校验 file 在索引中且当前用户可见，否则抛 404。"""
    d = doc_by_file(file)
    if not d or not can_see(user, d):
        raise HTTPException(status_code=404, detail="文档不存在")
    return file


@app.get("/api/bookmarks")
async def list_bookmarks(tag: str = "", user: str = Depends(require_session)):
    bm = bookmarks.bookmark_map(user)
    ctx = user_context(user)
    items = []
    for file, b in bm.items():
        d = doc_by_file(file)
        if not d or not can_see(user, d):
            continue  # 文档已不在索引或当前用户不可见，跳过展示（保留存储）
        if tag and tag not in b.get("tags", []):
            continue
        item = public_doc(d, user, ctx)
        item["bookmark_tags"] = b.get("tags", [])
        item["added"] = b.get("added", "")
        items.append(item)
    items.sort(key=lambda x: x.get("added", ""), reverse=True)
    return {"items": items, "facet": bookmarks.all_tags(user), "total": len(items)}


@app.post("/api/bookmarks")
async def add_bookmark(request: Request, user: str = Depends(require_session)):
    body = await request.json()
    file = _valid_file(str(body.get("file", "")), user)
    entry = bookmarks.add(user, file, body.get("tags") or [])
    return {"ok": True, "bookmarked": True,
            "bookmark_tags": entry["tags"], "added": entry["added"]}


@app.put("/api/bookmarks")
async def update_bookmark_tags(request: Request, user: str = Depends(require_session)):
    body = await request.json()
    file = _valid_file(str(body.get("file", "")), user)
    entry = bookmarks.set_tags(user, file, body.get("tags") or [])
    if entry is None:
        raise HTTPException(status_code=404, detail="尚未收藏该文档")
    return {"ok": True, "bookmark_tags": entry["tags"]}


@app.delete("/api/bookmarks")
async def remove_bookmark(request: Request, user: str = Depends(require_session)):
    body = await request.json()
    file = str(body.get("file", ""))
    removed = bookmarks.remove(user, file)
    return {"ok": True, "bookmarked": False, "removed": removed}


# ---------------- 文档可见性 ----------------

@app.post("/api/visibility")
async def set_visibility(request: Request, user: str = Depends(require_session)):
    """把文档设为个人/共享。权限 = 当前用户可见即可切换：
    共享 → 自己的个人；自己的个人 → 共享；管理员可切换任何可见文档（含他人的个人文档）。
    personal 的 owner 固定为当前用户。写入运行时覆盖层，无需重建索引。"""
    body = await request.json()
    file = _valid_file(str(body.get("file", "")), user)
    target = str(body.get("visibility", "")).strip().lower()
    if target not in ("shared", "personal"):
        raise HTTPException(status_code=400, detail="visibility 必须是 shared 或 personal")
    entry = visibility.set(file, target, owner=user)
    return {"ok": True, "file": file, "visibility": entry["visibility"], "owner": entry["owner"]}


# ---------------- 待删除标记（管理员） ----------------

PURGE_STATUS_PATH = DATA_DIR / "purge-status.json"


def _write_purge_status(result: str, detail: str = "", report: dict = None):
    try:
        PURGE_STATUS_PATH.write_text(json.dumps({
            "last_run": datetime.now(timezone.utc).isoformat(),
            "result": result, "detail": detail, "report": report,
        }, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass


def _run_purge():
    """待删除清理管道：purge 脚本 →（本机权威端再跑 publish.sh）→ sync_data → 热重载。

    KB_ROLE=primary（权威端）：purge 只暂存内容变更，publish.sh 负责 commit/push、
    重建索引与关联图并 webhook 通知对端。
    其他（副本端）：purge 用写权限部署密钥自行 --commit --push，随后本进程重建索引热重载，
    graph.json 保持旧版直到权威端下次 publish（/api/graph 按索引过滤节点，无脏数据外泄）。
    """
    env = dict(os.environ)
    env["KB_ROOT"] = str(KB_ROOT)
    is_primary = env.get("KB_ROLE") == "primary"
    try:
        cmd = [sys.executable, "-m", "libry.purge_marked"]
        if not is_primary:
            cmd += ["--commit", "--push"]
        pr = subprocess.run(cmd, cwd=str(KB_ROOT), capture_output=True, text=True,
                            timeout=900, env=env)
        try:
            report = json.loads(pr.stdout)
        except json.JSONDecodeError:
            report = None
        if pr.returncode != 0 or report is None:
            _write_purge_status("error", (pr.stderr or pr.stdout or "").strip()[-300:])
            return
        if report.get("push_error") or report.get("commit_error"):
            _write_purge_status("error", report.get("push_error") or report.get("commit_error"),
                                report)
            return
        if not report.get("deleted") and not report.get("reconciled"):
            _write_purge_status("empty", "没有待删除页面", report)
            return
        publish_script = ENGINE_ROOT / "deploy" / "publish.sh"
        if is_primary and report.get("deleted") and publish_script.exists():
            # publish.sh 提交暂存的删除、重建索引/graph、push 并通知对端
            pb = subprocess.run(["bash", str(publish_script)], cwd=str(KB_ROOT),
                                capture_output=True, text=True, timeout=1800, env=env)
            if pb.returncode != 0:
                _write_purge_status("error",
                                    "publish.sh 失败: " + (pb.stderr or pb.stdout).strip()[-300:],
                                    report)
                return
        # 推送 deletions.json 的 purged 终态（两端同一通道）
        _run_data_sync()
        # 本进程热重载（副本端让删除立即生效；权威端 publish.sh 已重建索引，这里再加载）
        indexer.build_index(str(KB_ROOT))
        load_index()
        deletions.reload()
        n = len(report.get("deleted") or [])
        m = sum((report.get("refs_cleaned") or {}).values())
        _write_purge_status("ok", f"删除 {n} 个页面，清理引用 {m} 处", report)
    except Exception as e:
        _write_purge_status("error", str(e)[:300])


@app.get("/api/deletions")
async def list_deletions(admin: str = Depends(require_admin)):
    items = []
    for file, e in sorted(deletions.pending_map().items(),
                          key=lambda kv: kv[1].get("marked_at") or "", reverse=True):
        d = doc_by_file(file)
        md_exists = (KB_ROOT / file).exists()
        items.append({
            "file": file,
            "title": (d or {}).get("title") or e.get("title") or file,
            "type": (d or {}).get("type") or e.get("type") or "",
            "marked_by": e.get("marked_by", ""),
            "marked_at": e.get("marked_at", ""),
            "exists": bool(d) and md_exists,  # False = 已不在索引/磁盘，purge 时会直接转终态
        })
    return {"items": items, "total": len(items)}


@app.post("/api/deletions")
async def mark_deletion(request: Request, admin: str = Depends(require_admin)):
    body = await request.json()
    file = _valid_file(str(body.get("file", "")), admin)
    d = doc_by_file(file)
    entry = deletions.mark(admin, file, title=(d or {}).get("title", ""),
                           type_=(d or {}).get("type", ""))
    return {"ok": True, "marked_deleted": True, "marked_at": entry["marked_at"]}


@app.delete("/api/deletions")
async def unmark_deletion(request: Request, admin: str = Depends(require_admin)):
    body = await request.json()
    removed = deletions.unmark(str(body.get("file", "")))
    return {"ok": True, "marked_deleted": False, "removed": removed}


@app.post("/api/deletions/execute")
async def execute_purge(request: Request, background_tasks: BackgroundTasks,
                        admin: str = Depends(require_admin)):
    """手动触发批量删除（管理员）：后台跑清理管道，立即 202；结果查 /api/deletions/status。"""
    ip = client_ip(request)
    if not purge_limiter.allow(ip):
        raise HTTPException(status_code=429, detail="操作过于频繁，请稍后再试")
    background_tasks.add_task(_run_purge)
    return JSONResponse({"ok": True, "message": "purge started"}, status_code=202)


@app.get("/api/deletions/status")
async def purge_status(user: str = Depends(require_session)):
    if PURGE_STATUS_PATH.exists():
        try:
            return json.loads(PURGE_STATUS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"last_run": None, "result": "never"}


# ---------------- 索引与同步 ----------------

def _check_sync_secret(request: Request):
    if not SYNC_SECRET or request.headers.get("X-Sync-Secret") != SYNC_SECRET:
        raise HTTPException(status_code=403, detail="无效的 X-Sync-Secret")


@app.post("/api/reindex")
async def reindex(request: Request):
    # session 或 X-Sync-Secret 二选一（后者供 sync.sh 调用）
    if not auth.check_request(request):
        _check_sync_secret(request)
    indexer.build_index(str(KB_ROOT))
    load_index()
    return {"ok": True, "doc_count": get_docs()["doc_count"]}


def _run_sync():
    if SYNC_SCRIPT.exists():
        subprocess.run(["bash", str(SYNC_SCRIPT)], cwd=str(KB_ROOT), timeout=600)


@app.post("/api/sync")
async def sync(request: Request, background_tasks: BackgroundTasks):
    """git push 后的 webhook：校验 secret + 限速，后台执行 sync.sh，立即返回 202。"""
    _check_sync_secret(request)
    ip = client_ip(request)
    if not sync_limiter.allow(ip):
        raise HTTPException(status_code=429, detail="同步请求过于频繁")
    background_tasks.add_task(_run_sync)
    return JSONResponse({"ok": True, "message": "sync started"}, status_code=202)


def _run_data_sync():
    subprocess.run([sys.executable, "-m", "libry.sync_data"], cwd=str(KB_ROOT), timeout=600)


@app.post("/api/sync-data/reload")
async def reload_synced_data(request: Request):
    """跨端同步写盘后，热重载本机进程内存中的用户数据（state + bookmarks + visibility + deletions）。"""
    _check_sync_secret(request)
    state.reload()
    bookmarks.reload()
    visibility.reload()
    deletions.reload()
    return {"ok": True}


@app.post("/api/sync-data")
async def sync_data(request: Request, background_tasks: BackgroundTasks,
                    user: str = Depends(require_admin)):
    """手动同步用户数据（管理员）：后台跑 sync_data，立即返回 202。"""
    ip = client_ip(request)
    if not data_sync_limiter.allow(ip):
        raise HTTPException(status_code=429, detail="同步请求过于频繁")
    background_tasks.add_task(_run_data_sync)
    return JSONResponse({"ok": True, "message": "data sync started"}, status_code=202)


@app.get("/api/sync-data/status")
async def sync_data_status(user: str = Depends(require_session)):
    if SYNC_STATUS_PATH.exists():
        try:
            return json.loads(SYNC_STATUS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"last_run": None, "result": "never"}


# ---------------- 前端静态文件（最后挂载，API 路由优先） ----------------

class NoCacheStaticFiles(StaticFiles):
    """静态资源每次使用前强制重验（ETag 未变更返回 304，代价极小）。

    浏览器对无 Cache-Control 的子资源会做启发式缓存且过期前不回源——
    no-cache 保证发版后所有端立即拿到新代码。
    """
    def file_response(self, full_path, stat_result, scope, status_code=200):
        resp = super().file_response(full_path, stat_result, scope, status_code)
        resp.headers["Cache-Control"] = "no-cache"
        return resp


if STATIC_DIR.exists():
    app.mount("/", NoCacheStaticFiles(directory=str(STATIC_DIR), html=True), name="static")


load_index()
