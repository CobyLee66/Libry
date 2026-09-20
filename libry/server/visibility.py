"""文档可见性覆盖层（按文件区分，服务器端 JSON 文件）。

visibility.json 结构：
{
  "files": {
    "wiki/sources/xxx.md": {"visibility": "personal", "owner": "alice", "updated_at": "2026-09-03T12:00:00+00:00"},
    ...
  }
}

每个条目是对该文件 frontmatter visibility/owner 的运行时覆盖（Web 端「设为个人/共享」
按钮写入）。生效规则：有覆盖记录用它，否则用索引中 frontmatter 的值——即 frontmatter
是初始状态，一旦在 Web 端切换过，以本文件为准。

按 file 为键、以 updated_at 做 LWW（跨端 sync_data.py 合并），每次切换都是显式写入，
无需删除墓碑；文档从库中移除后的残留条目无害（同 bookmarks）。
沿用 BookmarkStore 的模式：线程锁 + 临时文件原子替换。
"""
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_visibility(value) -> str:
    v = str(value or "shared").strip().lower()
    return v if v in ("shared", "personal") else "shared"


class VisibilityStore:
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
        for f, v in data["files"].items():
            if isinstance(v, dict) and v.get("visibility"):
                self._files[f] = {
                    "visibility": normalize_visibility(v["visibility"]),
                    "owner": str(v.get("owner") or "").strip(),
                    "updated_at": v.get("updated_at") or _now(),
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

    def get(self, file: str):
        """返回覆盖条目 {visibility, owner, updated_at}，无覆盖时返回 None。"""
        with self._lock:
            e = self._files.get(file)
            return dict(e) if e else None

    def set(self, file: str, visibility: str, owner: str) -> dict:
        """写入覆盖条目并落盘；personal 必须有 owner，shared 清空 owner。"""
        visibility = normalize_visibility(visibility)
        if visibility == "personal":
            owner = str(owner or "").strip()
        else:
            owner = ""
        with self._lock:
            entry = {"visibility": visibility, "owner": owner, "updated_at": _now()}
            self._files[file] = entry
            self._save()
            return dict(entry)
