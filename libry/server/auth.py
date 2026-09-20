"""多账户认证：用户名+密码（bcrypt）+ itsdangerous 签名 session cookie + 登录限速。

users.json 结构（<data>/users.json，权限 600）：
{
  "users": {
    "admin": {"password_hash": "$2b$12$...", "admin": true},
    ...
  }
}

首次启动（users.json 不存在）时用环境变量 KB_PASSWORD_HASH 创建 admin 账户。
此前单用户版本的 data/auth.json 覆盖哈希会被迁移为 admin 的初始密码。
"""
import json
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

import bcrypt
from fastapi import HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SESSION_COOKIE = "kb_session"
SESSION_MAX_AGE = 7 * 24 * 3600  # 7 天


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RateLimiter:
    """内存滑动窗口限速器。"""

    def __init__(self, max_hits: int, window_sec: int):
        self.max_hits = max_hits
        self.window = window_sec
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.max_hits:
                return False
            q.append(now)
            return True


class Auth:
    def __init__(self, users_path, session_secret: str, cookie_secure: bool = False,
                 bootstrap_hash: str = "", legacy_auth_path=None):
        if not session_secret:
            raise RuntimeError("环境变量 SESSION_SECRET 未设置（openssl rand -hex 32）")
        self._users_path = Path(users_path)
        self._lock = threading.Lock()
        self._serializer = URLSafeTimedSerializer(session_secret, salt="kb-session")
        self.cookie_secure = cookie_secure
        self.login_limiter = RateLimiter(max_hits=5, window_sec=60)
        if not self._users_path.exists():
            # 旧版 auth.json 的覆盖哈希优先于环境变量
            initial = bootstrap_hash
            if legacy_auth_path and Path(legacy_auth_path).exists():
                try:
                    data = json.loads(Path(legacy_auth_path).read_text(encoding="utf-8"))
                    initial = data.get("password_hash") or bootstrap_hash
                except (ValueError, OSError):
                    pass
            if not initial:
                raise RuntimeError("环境变量 KB_PASSWORD_HASH 未设置（bcrypt 哈希）")
            self._save_users({"admin": {"password_hash": initial, "admin": True}})

    # ---------------- 用户存储 ----------------

    def _load_users(self) -> dict:
        try:
            data = json.loads(self._users_path.read_text(encoding="utf-8"))
            return data.get("users") or {}
        except (ValueError, OSError):
            return {}

    def _save_users(self, users: dict):
        self._users_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._users_path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"users": users}, ensure_ascii=False), encoding="utf-8")
        os.chmod(tmp, 0o600)
        tmp.replace(self._users_path)

    def list_users(self) -> list:
        with self._lock:
            return [{"username": name, "admin": bool(u.get("admin"))}
                    for name, u in sorted(self._load_users().items())
                    if not u.get("deleted")]

    def is_admin(self, username: str) -> bool:
        with self._lock:
            u = self._load_users().get(username)
            return bool(u and not u.get("deleted") and u.get("admin"))

    def verify(self, username: str, password: str) -> bool:
        with self._lock:
            u = self._load_users().get(username)
        if not u or u.get("deleted"):
            return False
        try:
            return bcrypt.checkpw(password.encode(), u["password_hash"].encode())
        except (ValueError, KeyError):
            return False

    def set_password(self, username: str, new_password: str):
        with self._lock:
            users = self._load_users()
            if username not in users or users[username].get("deleted"):
                raise HTTPException(status_code=404, detail="用户不存在")
            users[username]["password_hash"] = bcrypt.hashpw(
                new_password.encode(), bcrypt.gensalt()).decode()
            users[username]["updated_at"] = _now()
            self._save_users(users)

    def add_user(self, username: str, password: str, admin: bool = False):
        username = username.strip()
        if not username or len(username) > 32 or not all(
                c.isalnum() or c in "-_." for c in username):
            raise HTTPException(status_code=400, detail="用户名仅限字母、数字、- _ .")
        if len(password) < 8:
            raise HTTPException(status_code=400, detail="密码至少 8 位")
        with self._lock:
            users = self._load_users()
            if username in users and not users[username].get("deleted"):
                raise HTTPException(status_code=400, detail="用户名已存在")
            users[username] = {
                "password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
                "admin": bool(admin),
                "updated_at": _now(),
            }
            self._save_users(users)

    def delete_user(self, username: str, by_user: str):
        with self._lock:
            users = self._load_users()
            if username not in users or users[username].get("deleted"):
                raise HTTPException(status_code=404, detail="用户不存在")
            if username == by_user:
                raise HTTPException(status_code=400, detail="不能删除当前登录账户")
            if users[username].get("admin") and \
                    sum(1 for u in users.values() if u.get("admin")) <= 1:
                raise HTTPException(status_code=400, detail="不能删除唯一的管理员")
            users[username] = {"deleted": _now()}  # 墓碑：跨端同步不复活已删账户
            self._save_users(users)

    # ---------------- 会话 ----------------

    def issue_session(self, response: Response, username: str):
        token = self._serializer.dumps({"u": username})
        response.set_cookie(
            SESSION_COOKIE, token,
            max_age=SESSION_MAX_AGE, httponly=True,
            secure=self.cookie_secure, samesite="lax",
        )

    def clear_session(self, response: Response):
        response.delete_cookie(SESSION_COOKIE)

    def current_user(self, request: Request):
        """返回会话中的用户名，未登录/过期返回 None。"""
        token = request.cookies.get(SESSION_COOKIE)
        if not token:
            return None
        try:
            data = self._serializer.loads(token, max_age=SESSION_MAX_AGE)
        except (BadSignature, SignatureExpired):
            return None
        username = data.get("u", "")
        with self._lock:
            u = self._load_users().get(username)
            if not u or u.get("deleted"):
                return None  # 账户被删除后旧会话立即失效
        return username

    def check_request(self, request: Request) -> bool:
        return self.current_user(request) is not None


def make_session_dependency(auth: Auth):
    """FastAPI 依赖：校验 session cookie，失败抛 401，成功返回用户名。"""
    def require_session(request: Request) -> str:
        user = auth.current_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="未登录或会话已过期")
        return user
    return require_session


def make_admin_dependency(auth: Auth):
    """FastAPI 依赖：要求管理员账户。"""
    def require_admin(request: Request) -> str:
        user = auth.current_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="未登录或会话已过期")
        if not auth.is_admin(user):
            raise HTTPException(status_code=403, detail="需要管理员权限")
        return user
    return require_admin
