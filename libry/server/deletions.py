"""待删除标记存储（按文件全局，服务器端 JSON 文件）。

deletions.json 结构：
{
  "files": {
    "wiki/concepts/xxx.md": {"marked_by": "admin", "marked_at": "2026-09-19T12:00:00+00:00",
                             "title": "Xxx", "type": "concepts"},
    "wiki/sources/yyy.md": {"deleted": "2026-09-19T13:00:00+00:00"},   // 取消标记墓碑
    "wiki/sources/zzz.md": {"purged": "2026-09-20T04:00:00+00:00", "purged_by": "mac"},  // 已清理终态
    ...
  }
}

语义：标记删除是全局动作（不分账户），仅管理员可写。
- pending  = 条目含 marked_at 且无更新的 deleted/purged
- 取消标记 = 写 {"deleted": ts} 墓碑（跨端同步 LWW 需要，防对端旧状态复活标记）
- 清理完成 = 写 {"purged": ts, "purged_by": node} 终态（永久保留，防对端旧 pending 复活）
墓碑与 purged 条目永久保留（同 bookmarks 的删除墓碑语义），文件体积极小。
沿用 BookmarkStore 的模式：线程锁 + 临时文件原子替换。
"""
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _entry_ts(e: dict) -> str:
    """条目的 LWW 时间戳：purged > deleted > marked_at 中存在的最新值。"""
    return e.get("purged") or e.get("deleted") or e.get("marked_at") or ""


class DeletionStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self._files = {}
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if not isinstance(data, dict) or not isinstance(data.get("files"), dict):
            return
        for f, e in data["files"].items():
            if not isinstance(e, dict):
                continue
            if e.get("purged"):
                self._files[f] = {"purged": e["purged"],
                                  "purged_by": str(e.get("purged_by") or "")}
            elif e.get("deleted"):
                self._files[f] = {"deleted": e["deleted"]}
            elif e.get("marked_at"):
                self._files[f] = {
                    "marked_by": str(e.get("marked_by") or ""),
                    "marked_at": e["marked_at"],
                    "title": str(e.get("title") or ""),
                    "type": str(e.get("type") or ""),
                }

    def reload(self):
        """重读磁盘（跨端同步后由 /api/sync-data/reload 触发）。"""
        with self._lock:
            self._files = {}
            self._load()

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"files": self._files}, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        os.chmod(tmp, 0o600)
        tmp.replace(self.path)

    def is_pending(self, e: dict) -> bool:
        return bool(e) and not e.get("deleted") and not e.get("purged")

    def pending_map(self) -> dict:
        """file → 标记条目（仅 pending）。"""
        with self._lock:
            return {f: dict(e) for f, e in self._files.items() if self.is_pending(e)}

    def marked_set(self) -> set:
        with self._lock:
            return {f for f, e in self._files.items() if self.is_pending(e)}

    def purged_map(self) -> dict:
        with self._lock:
            return {f: dict(e) for f, e in self._files.items() if e.get("purged")}

    def mark(self, username: str, file: str, title: str = "", type_: str = "") -> dict:
        with self._lock:
            entry = {"marked_by": username, "marked_at": _now(),
                     "title": title, "type": type_}
            self._files[file] = entry
            self._save()
            return dict(entry)

    def unmark(self, file: str) -> bool:
        with self._lock:
            e = self._files.get(file)
            if not self.is_pending(e):
                return False
            self._files[file] = {"deleted": _now()}  # 墓碑：跨端同步不复活标记
            self._save()
            return True

    def mark_purged(self, files, node: str = ""):
        with self._lock:
            ts = _now()
            for f in files:
                self._files[f] = {"purged": ts, "purged_by": node}
            self._save()
