"""收藏夹存储（按账户区分，服务器端 JSON 文件）。

bookmarks.json 结构：
{
  "users": {
    "admin": {
      "wiki/concepts/xxx.md": {"added": "2026-08-15T12:00:00+00:00", "tags": ["标签A"]},
      ...
    }
  }
}

以 file 为键，天然去重。tags 为用户自定义收藏标签（与知识库标准 tag 无关，
不登记到 tags.md）。沿用 StateStore 的模式：线程锁 + 临时文件原子替换。
"""
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_tags(tags) -> list:
    """规范化收藏标签：拆分中英文逗号/顿号、去空白、去重、过滤空串、限长。"""
    if not tags:
        return []
    if isinstance(tags, str):
        tags = [tags]
    out = []
    seen = set()
    for raw in tags:
        for part in str(raw).replace("，", ",").replace("、", ",").split(","):
            t = part.strip()
            if t and t not in seen:
                seen.add(t)
                out.append(t[:40])
    return out


class BookmarkStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self._users = {}
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if not isinstance(data, dict) or not isinstance(data.get("users"), dict):
            return
        for name, u in data["users"].items():
            if not isinstance(u, dict):
                continue
            entry = {}
            for f, b in u.items():
                if isinstance(b, dict):
                    if b.get("deleted"):
                        entry[f] = {"deleted": b["deleted"]}  # 保留删除墓碑
                    else:
                        entry[f] = {
                            "added": b.get("added") or _now(),
                            "updated_at": b.get("updated_at") or b.get("added") or _now(),
                            "tags": normalize_tags(b.get("tags")),
                        }
            self._users[name] = entry

    def reload(self):
        """重读磁盘（跨端同步后由 /api/sync-data/reload 触发）。"""
        with self._lock:
            self._users = {}
            self._load()

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"users": self._users}, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        os.chmod(tmp, 0o600)
        tmp.replace(self.path)

    def _user(self, username: str) -> dict:
        """调用方须持有 self._lock。"""
        if username not in self._users:
            self._users[username] = {}
        return self._users[username]

    def bookmark_map(self, username: str) -> dict:
        with self._lock:
            return {f: b for f, b in self._user(username).items() if not b.get("deleted")}

    def bookmark_set(self, username: str) -> set:
        with self._lock:
            return {f for f, b in self._user(username).items() if not b.get("deleted")}

    def add(self, username: str, file: str, tags) -> dict:
        with self._lock:
            u = self._user(username)
            existing = u.get(file)
            entry = {
                "added": (existing or {}).get("added") or _now(),
                "updated_at": _now(),
                "tags": normalize_tags(tags),
            }
            u[file] = entry
            self._save()
            return entry

    def set_tags(self, username: str, file: str, tags):
        with self._lock:
            u = self._user(username)
            if file not in u or u[file].get("deleted"):
                return None
            u[file]["tags"] = normalize_tags(tags)
            u[file]["updated_at"] = _now()
            self._save()
            return u[file]

    def remove(self, username: str, file: str) -> bool:
        with self._lock:
            u = self._user(username)
            if file not in u or u[file].get("deleted"):
                return False
            u[file] = {"deleted": _now()}  # 墓碑：跨端同步不复活已删收藏
            self._save()
            return True

    def get_tags(self, username: str, file: str) -> list:
        with self._lock:
            b = self._user(username).get(file)
            return list(b["tags"]) if b and not b.get("deleted") else []

    def all_tags(self, username: str) -> dict:
        """返回 {tag: count}，供收藏夹标签筛选 facet。"""
        with self._lock:
            counts = {}
            for b in self._user(username).values():
                if b.get("deleted"):
                    continue
                for t in b.get("tags", []):
                    counts[t] = counts.get(t, 0) + 1
            return counts
