"""离线数据通道 API 测试：manifest 可见性、offline/doc 无副作用、素材路由权限与
穿越防护、写端点可选 updated_at（离线回放的 LWW 依据）。"""
import hashlib
import importlib
from datetime import datetime, timezone

import bcrypt
import pytest

from libry.server.util import coerce_updated_at

PASSWORD = "test-password-123"


@pytest.fixture()
def server(vault, monkeypatch):
    """以临时 vault 为根加载 server.main 单例，返回 (TestClient, 模块)。"""
    monkeypatch.setenv("SESSION_SECRET", "unit-test-secret")
    monkeypatch.setenv("KB_ROOT", str(vault))
    monkeypatch.delenv("KB_DATA_DIR", raising=False)
    monkeypatch.setenv("KB_PASSWORD_HASH",
                       bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode())
    from libry.server import main as m
    importlib.reload(m)
    from fastapi.testclient import TestClient
    return TestClient(m.app), m


def _login(client, username="admin", password=PASSWORD):
    r = client.post("/api/login", json={"username": username, "password": password})
    assert r.status_code == 200
    return r


def _add_reader(client):
    """管理员身份建一个非管理员账户（保持当前会话不变）。"""
    r = client.post("/api/users", json={"username": "reader", "password": "reader-pass-123"})
    assert r.status_code == 200


def _switch_user(client, username="reader", password="reader-pass-123"):
    client.post("/api/logout")
    _login(client, username, password)


def _set_personal(client, file):
    r = client.post("/api/visibility", json={"file": file, "visibility": "personal"})
    assert r.status_code == 200


def test_offline_endpoints_require_auth(server):
    client, m = server
    assert client.get("/api/offline/manifest").status_code == 401
    assert client.get("/api/offline/doc",
                      params={"file": "wiki/concepts/bar-concept.md"}).status_code == 401


def test_offline_manifest_visibility_and_hash(server, vault):
    client, m = server
    _login(client)
    _add_reader(client)
    _set_personal(client, "wiki/sources/foo-article.md")

    admin_manifest = client.get("/api/offline/manifest").json()
    assert "wiki/sources/foo-article.md" in admin_manifest["docs"]
    assert admin_manifest["generated_at"]

    # reader：个人文档不出现在清单中，共享文档（wiki + archive）保留
    _switch_user(client)
    manifest = client.get("/api/offline/manifest").json()
    assert "wiki/sources/foo-article.md" not in manifest["docs"]
    assert "wiki/concepts/bar-concept.md" in manifest["docs"]
    assert "notes/note-1.md" in manifest["docs"]

    entry = manifest["docs"]["wiki/concepts/bar-concept.md"]
    assert entry["title"] == "Bar Concept"
    assert entry["type"] == "concepts"
    want = hashlib.sha256((vault / "wiki/concepts/bar-concept.md").read_bytes()).hexdigest()
    assert entry["hash"] == want


def test_offline_doc_no_read_side_effect(server):
    client, m = server
    _login(client)
    r = client.get("/api/offline/doc", params={"file": "wiki/concepts/bar-concept.md"})
    assert r.status_code == 200
    body = r.json()
    assert "<h1" in body["html"] and "Bar Concept" in body["html"]
    assert body["meta"]["file"] == "wiki/concepts/bar-concept.md"

    def read_flag():
        items = client.get("/api/docs", params={"page_size": 50}).json()["items"]
        return next(d for d in items
                    if d["file"] == "wiki/concepts/bar-concept.md")["read"]

    assert read_flag() is False  # 离线预取不产生已读副作用
    assert client.get("/api/doc",
                      params={"file": "wiki/concepts/bar-concept.md"}).status_code == 200
    assert read_flag() is True   # 对照：在线阅读通道打开即标已读


def test_offline_doc_rate_limit_retry_after_and_separate_manifest(server):
    """逐篇限速返回 429 + Retry-After；清单端点独立限速，不被整库下载耗尽。"""
    client, m = server
    _login(client)
    params = {"file": "wiki/concepts/bar-concept.md"}
    m.offline_doc_limiter.max_hits = 1

    assert client.get("/api/offline/doc", params=params).status_code == 200
    r = client.get("/api/offline/doc", params=params)
    assert r.status_code == 429
    assert r.json()["detail"] == "rate_limited"
    assert 1 <= int(r.headers["retry-after"]) <= 60
    # 逐篇被限速时清单仍可用：否则用户重试时连清单都拿不到
    assert client.get("/api/offline/manifest").status_code == 200


def test_offline_doc_personal_404_indistinguishable(server):
    client, m = server
    _login(client)
    _add_reader(client)
    _set_personal(client, "wiki/sources/foo-article.md")
    _switch_user(client)
    r1 = client.get("/api/offline/doc", params={"file": "wiki/sources/foo-article.md"})
    r2 = client.get("/api/offline/doc", params={"file": "no/such/file.md"})
    assert r1.status_code == r2.status_code == 404
    assert r1.json()["detail"] == r2.json()["detail"] == "doc_not_found"


def test_assets_auth_and_traversal(server, vault):
    client, m = server
    assets = vault / "raw" / "assets"
    assets.mkdir(parents=True)
    (assets / "pic.png").write_bytes(b"\x89PNG fake")
    (vault / "secret.md").write_text("# secret", encoding="utf-8")

    # 未登录一律 401
    assert client.get("/raw/assets/pic.png").status_code == 401
    _login(client)

    r = client.get("/raw/assets/pic.png")
    assert r.status_code == 200
    assert r.content == b"\x89PNG fake"
    assert r.headers["Cache-Control"] == "private, no-cache"

    # 目录穿越与 raw/ 其余内容不暴露（编码与未编码两种形态都不允许 200）
    for path in ("/raw/assets/%2e%2e/secret.md", "/raw/assets/..%2fsecret.md",
                 "/raw/assets/%2e%2e/%2e%2e/libry.toml", "/raw/secret.md"):
        assert client.get(path).status_code != 200, path


def test_write_endpoints_accept_client_updated_at(server):
    client, m = server
    _login(client)
    past = "2020-03-04T05:06:07+00:00"

    # 过去时间作为 LWW 时间戳存储
    r = client.post("/api/marks", json={"file": "wiki/concepts/bar-concept.md",
                                        "scroll": 10, "pct": 0.2, "updated_at": past})
    assert r.status_code == 200 and r.json()["updated_at"] == past
    marks = client.get("/api/marks").json()["marks"]
    assert marks[0]["pos_updated_at"] == past

    # 未来时间钳制为服务器当前时间
    r = client.post("/api/state/progress",
                    json={"file": "wiki/concepts/bar-concept.md", "scroll": 5,
                          "pct": 0.3, "updated_at": "2099-01-01T00:00:00+00:00"})
    assert r.status_code == 200
    prog = client.get("/api/marks").json()["progress"]
    assert datetime.fromisoformat(prog[0]["pos_updated_at"]).year < 2099

    # 非法格式回退服务器时间（不 500）
    r = client.post("/api/bookmarks", json={"file": "wiki/concepts/bar-concept.md",
                                            "tags": ["x"], "updated_at": "not-a-time"})
    assert r.status_code == 200

    # 删除墓碑时间同样采用客户端值
    r = client.request("DELETE", "/api/marks", json={"file": "wiki/concepts/bar-concept.md",
                                                     "updated_at": past})
    assert r.status_code == 200
    assert client.get("/api/marks").json()["marks"] == []


def test_coerce_updated_at_unit():
    # 缺省/非法 → 合法 ISO 的服务器当前时间
    for v in (None, "", "garbage", 12345):
        assert datetime.fromisoformat(coerce_updated_at(v))
    # 过去时间原样保留
    assert coerce_updated_at("2020-03-04T05:06:07+00:00") == "2020-03-04T05:06:07+00:00"
    # 无时区按 UTC 补齐
    assert coerce_updated_at("2020-03-04T05:06:07") == "2020-03-04T05:06:07+00:00"
    # 未来值钳制
    assert datetime.fromisoformat(
        coerce_updated_at("2099-01-01T00:00:00+00:00")) <= datetime.now(timezone.utc)
