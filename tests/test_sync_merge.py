"""sync_data 的五个合并函数（LWW + 墓碑，纯函数）。"""
from libry.sync_data import merge_bookmarks, merge_deletions, merge_state, merge_users, merge_visibility


def test_merge_users_lww_and_tombstone():
    local = {"users": {"alice": {"password_hash": "h1", "admin": True, "updated_at": "2026-01-01T00:00:00+00:00"},
                       "bob": {"password_hash": "h2", "admin": False, "deleted": "2026-01-05T00:00:00+00:00"}}}
    remote = {"users": {"alice": {"password_hash": "h3", "admin": True, "updated_at": "2026-01-03T00:00:00+00:00"},
                        "bob": {"password_hash": "h2", "admin": False, "updated_at": "2026-01-02T00:00:00+00:00"},
                        "carol": {"password_hash": "h4", "admin": False}}}
    out = merge_users(local, remote)
    assert out["users"]["alice"]["password_hash"] == "h3"        # 远端较新
    assert "deleted" in out["users"]["bob"]                       # 墓碑保留
    assert out["users"]["carol"]["password_hash"] == "h4"         # 远端独有


def test_merge_users_tie_takes_remote():
    ts = "2026-01-01T00:00:00+00:00"
    local = {"users": {"a": {"password_hash": "L", "updated_at": ts}}}
    remote = {"users": {"a": {"password_hash": "R", "updated_at": ts}}}
    assert merge_users(local, remote)["users"]["a"]["password_hash"] == "R"


def test_merge_state_read_union_and_watermark_max():
    local = {"users": {"a": {"read": {"f1": "2026-01-01T00:00:00+00:00"},
                             "new_since": "2026-01-01T00:00:00+00:00", "pending_since": None}}}
    remote = {"users": {"a": {"read": {"f2": "2026-01-02T00:00:00+00:00", "f1": "2025-12-31T00:00:00+00:00"},
                              "new_since": "2026-01-05T00:00:00+00:00", "pending_since": "2026-01-06T00:00:00+00:00"}}}
    out = merge_state(local, remote)["users"]["a"]
    assert out["read"]["f1"] == "2026-01-01T00:00:00+00:00"      # 逐文件取更晚
    assert out["read"]["f2"] == "2026-01-02T00:00:00+00:00"      # 并集
    assert out["new_since"] == "2026-01-05T00:00:00+00:00"       # 水位取最大


def test_merge_bookmarks_tombstone_wins():
    local = {"users": {"a": {"f1": {"added": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-01T00:00:00+00:00", "tags": []}}}}
    remote = {"users": {"a": {"f1": {"deleted": "2026-01-02T00:00:00+00:00"}}}}
    out = merge_bookmarks(local, remote)["users"]["a"]
    assert out["f1"] == {"deleted": "2026-01-02T00:00:00+00:00"}


def test_merge_visibility_lww():
    local = {"files": {"f1": {"visibility": "shared", "owner": "", "updated_at": "2026-01-01T00:00:00+00:00"}}}
    remote = {"files": {"f1": {"visibility": "personal", "owner": "alice", "updated_at": "2026-01-04T00:00:00+00:00"}}}
    out = merge_visibility(local, remote)
    assert out["files"]["f1"]["visibility"] == "personal"
    # 切回 shared 也是显式写入（owner 清空），按 LWW 覆盖
    back = {"files": {"f1": {"visibility": "shared", "owner": "", "updated_at": "2026-01-09T00:00:00+00:00"}}}
    out2 = merge_visibility(out, back)
    assert out2["files"]["f1"]["visibility"] == "shared"


def test_merge_deletions_state_priority():
    local = {"files": {"f1": {"marked_by": "admin", "marked_at": "2026-01-02T00:00:00+00:00"}}}
    remote = {"files": {"f1": {"deleted": "2026-01-05T00:00:00+00:00"}}}
    out = merge_deletions(local, remote)
    assert out["files"]["f1"] == {"deleted": "2026-01-05T00:00:00+00:00"}   # 取消标记墓碑生效
    purged = {"files": {"f1": {"purged": "2026-01-09T00:00:00+00:00", "purged_by": "n1"}}}
    out2 = merge_deletions(out, purged)
    assert out2["files"]["f1"]["purged"] == "2026-01-09T00:00:00+00:00"    # purged 终态最新
    # 幂等
    assert merge_deletions(out2, out2) == out2
