"""已读/新增状态存储（按账户区分，服务器端 JSON 文件）。

state.json 结构：
{
  "users": {
    "admin": {
      "read": {"wiki/concepts/xxx.md": "2026-08-15T07:00:00+00:00", ...},
      "new_since": "2026-08-15T07:00:00+00:00",   // “新增”水位线
      "pending_since": "2026-08-15T08:00:00+00:00", // 本次登录时间，ack 后推进 new_since
      "progress": {"wiki/concepts/xxx.md": {"scroll": 1234, "pct": 0.42,
                                             "updated_at": "..."}, ...},
      "marks": {"wiki/concepts/yyy.md": {"scroll": 567, "pct": 0.18,
                                          "updated_at": "..."}, ...}
    }
  }
}

旧版单用户格式（顶层 read/new_since/pending_since）自动迁移到 admin 账户下；
旧版缺少 progress/marks 键的文件读取时按空表兼容。

语义：
- 未读 = 不在该账户 read 集合中
- 新增 = created 日期 > 该账户 new_since 日期 且未读
- 首次登录时将 new_since 初始化为当时时间，之后固定不再推进；
  文章只有标记已读后才移出新增列表（ack_new 接口保留但前端已不再调用）
- progress = 自动阅读进度（滚动时防抖上报），pct >= 0.98 视为读完即清除条目，
  因此该表只保留「读到一半」的文档，天然有界
- marks = 手动书签（每篇文档一个，记录添加时的滚动位置），删除留墓碑防同步复活

写入策略（2026-09-05 起）：mark_read/mark_unread/save_progress 只改内存 + 脏标记，
30 秒防抖落盘——打开文档即自动标已读、滚动即上报进度是最高频写操作，逐次全量
重写 JSON 的写放大在文档量增长后不可忽视。进程退出经 atexit 与 FastAPI shutdown
钩子双路径强制刷盘（uvicorn 收到 SIGTERM 优雅退出时不执行 atexit，单靠它会丢
防抖窗口内的改动）；/api/sync-data/reload 触发的 reload 会先把未落盘的本地改动
按 file 级 LWW 合并进磁盘数据，不被跨端同步覆盖。marks 是低频显式操作，即时落盘
（同 on_login）。取舍：进程被 SIGKILL 时最多丢 30 秒内的已读标记与阅读进度。
"""
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

FLUSH_DEBOUNCE_SEC = 30


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_user() -> dict:
    return {"read": {}, "new_since": None, "pending_since": None,
            "progress": {}, "marks": {}}


class StateStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self._users = {}
        self._dirty = False
        self._timer = None
        self._load()

    def _parse(self) -> dict:
        """读取 state.json 并解析为 {user: entry}；文件缺失/损坏返回空。"""
        users = {}
        if not self.path.exists():
            return users
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return users
        if not isinstance(data, dict):
            return users
        if isinstance(data.get("users"), dict):
            source = data["users"]
        elif "read" in data or "new_since" in data:
            source = {"admin": data}  # 旧版单用户格式 → 迁移到 admin
        else:
            return users
        for name, u in source.items():
            if isinstance(u, dict):
                entry = _empty_user()
                entry["read"] = dict(u.get("read") or {})
                entry["new_since"] = u.get("new_since")
                entry["pending_since"] = u.get("pending_since")
                for key in ("progress", "marks"):
                    raw = u.get(key)
                    if isinstance(raw, dict):
                        entry[key] = {f: b for f, b in raw.items() if isinstance(b, dict)}
                users[name] = entry
        return users

    def _load(self):
        self._users = self._parse()

    def _save(self):
        """调用方须持有 self._lock。全量写盘后内存与磁盘一致，清除脏标记。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"users": self._users}, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        tmp.replace(self.path)
        self._dirty = False

    def _schedule_flush(self):
        """调用方须持有 self._lock。防抖落盘：窗口内的多次标记合并为一次写盘。"""
        if self._timer is None:
            self._timer = threading.Timer(FLUSH_DEBOUNCE_SEC, self._flush)
            self._timer.daemon = True
            self._timer.start()

    def _flush(self):
        with self._lock:
            self._timer = None
            if self._dirty:
                self._save()

    def flush(self):
        """立即落盘未写入的改动（进程退出等关键节点调用）。"""
        self._flush()

    def _user(self, username: str) -> dict:
        """调用方须持有 self._lock。"""
        if username not in self._users:
            self._users[username] = _empty_user()
        return self._users[username]

    def reload(self):
        """重读磁盘（跨端同步后由 /api/sync-data/reload 触发）。

        有未落盘的本地改动时，按 file 级 LWW 合并进刚读到的磁盘数据并立即
        回写——防抖窗口内的已读标记不会被跨端同步覆盖，也不会因进程重启丢失。
        已知取舍：窗口内的 mark_unread 遇到并发跨端合并可能被旧记录复活
        （再次标记即自愈）。
        """
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            disk_users = self._parse()
            if self._dirty:
                for name, u in self._users.items():
                    du = disk_users.setdefault(name, _empty_user())
                    for f, ts in u["read"].items():
                        old = du["read"].get(f)
                        if not old or ts > old:
                            du["read"][f] = ts
                    for key in ("new_since", "pending_since"):
                        if u[key] and (not du.get(key) or u[key] > du[key]):
                            du[key] = u[key]
                    # 防抖窗口内的进度按 file 级 LWW 合入；窗口内被清除的进度
                    # 遇到并发同步的旧条目可能复活（再次滚动即自愈，同 mark_unread）
                    for f, p in u["progress"].items():
                        old = du["progress"].get(f)
                        if not old or (p.get("updated_at") or "") > (old.get("updated_at") or ""):
                            du["progress"][f] = p
            self._users = disk_users
            if self._dirty:
                self._save()
            self._dirty = False

    def read_set(self, username: str) -> set:
        with self._lock:
            return set(self._user(username)["read"].keys())

    def read_map(self, username: str) -> dict:
        """file → 已读时间戳 的拷贝，供已读列表按时间排序。"""
        with self._lock:
            return dict(self._user(username)["read"])

    def mark_read(self, username: str, files):
        with self._lock:
            ts = _now()
            read = self._user(username)["read"]
            for f in files:
                read[f] = ts
            self._dirty = True
            self._schedule_flush()

    def mark_unread(self, username: str, files):
        with self._lock:
            read = self._user(username)["read"]
            for f in files:
                read.pop(f, None)
            self._dirty = True
            self._schedule_flush()

    # ---------------- 阅读进度（自动） ----------------

    def save_progress(self, username: str, file: str, scroll: int, pct: float):
        """滚动时防抖上报：pct >= 0.98 视为读完，清除该文档进度条目。"""
        with self._lock:
            progress = self._user(username)["progress"]
            if pct >= 0.98:
                if file not in progress:
                    return
                progress.pop(file, None)
            else:
                progress[file] = {"scroll": max(0, int(scroll)),
                                  "pct": min(max(float(pct), 0.0), 1.0),
                                  "updated_at": _now()}
            self._dirty = True
            self._schedule_flush()

    def clear_progress(self, username: str, file: str):
        with self._lock:
            if self._user(username)["progress"].pop(file, None) is not None:
                self._dirty = True
                self._schedule_flush()

    def progress_map(self, username: str) -> dict:
        with self._lock:
            return dict(self._user(username)["progress"])

    # ---------------- 手动书签 ----------------

    def set_mark(self, username: str, file: str, scroll: int, pct: float) -> dict:
        """添加/更新书签（每篇文档一个，记录添加时的滚动位置）。低频显式操作，即时落盘。"""
        with self._lock:
            entry = {"scroll": max(0, int(scroll)),
                     "pct": min(max(float(pct), 0.0), 1.0),
                     "updated_at": _now()}
            self._user(username)["marks"][file] = entry
            self._save()
            return entry

    def remove_mark(self, username: str, file: str) -> bool:
        with self._lock:
            marks = self._user(username)["marks"]
            if file not in marks or marks[file].get("deleted"):
                return False
            marks[file] = {"deleted": _now()}  # 墓碑：跨端同步不复活已删书签
            self._save()
            return True

    def mark_map(self, username: str) -> dict:
        with self._lock:
            return {f: b for f, b in self._user(username)["marks"].items()
                    if not b.get("deleted")}

    def on_login(self, username: str):
        """登录成功：记录本次登录时间为待推进水位；首次登录时初始化水位为现在（避免全部文档都算新增）。"""
        with self._lock:
            now = _now()
            u = self._user(username)
            if not u["new_since"]:
                u["new_since"] = now
            u["pending_since"] = now
            self._save()

    def ack_new(self, username: str):
        """进入“新增”tab 后调用：把水位推进到本次登录时间。"""
        with self._lock:
            u = self._user(username)
            if u["pending_since"]:
                u["new_since"] = u["pending_since"]
                self._save()

    def new_since_date(self, username: str) -> str:
        with self._lock:
            v = self._user(username)["new_since"]
            return (v or "")[:10]

    def is_new(self, username: str, doc_created: str, is_read: bool) -> bool:
        if is_read or not doc_created:
            return False
        since = self.new_since_date(username)
        return bool(since) and doc_created > since
