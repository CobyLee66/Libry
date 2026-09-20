"""libry init 脚手架（非交互：密码走环境变量）。"""
import json

import pytest

from libry.__main__ import main as cli_main


@pytest.fixture()
def init_env(monkeypatch, tmp_path):
    monkeypatch.delenv("KB_ROOT", raising=False)
    monkeypatch.delenv("KB_DATA_DIR", raising=False)
    monkeypatch.setenv("LIBRY_ADMIN_PASSWORD", "test-pass-123")
    return tmp_path / "newvault"


def test_init_creates_vault(init_env):
    rc = cli_main(["init", str(init_env), "--title", "我的库", "--no-git"])
    assert rc == 0
    assert (init_env / "AGENTS.md").is_file()
    assert (init_env / "libry.toml").is_file()
    assert 'title = "我的库"' in (init_env / "libry.toml").read_text(encoding="utf-8")
    # 点路径落位
    assert (init_env / ".gitignore").is_file()
    assert (init_env / ".agents" / "skills" / "kb-ingest" / "SKILL.md").is_file()
    assert not (init_env / "gitignore-template").exists()
    assert not (init_env / "agent-skills").exists()
    for d in ("sources", "entities", "concepts", "synthesis"):
        assert (init_env / "wiki" / d).is_dir()
    # 密钥与账户
    env_text = (init_env / ".env").read_text(encoding="utf-8")
    assert "SESSION_SECRET='" in env_text and "SYNC_SECRET='" in env_text
    users = json.loads((init_env / ".libry" / "users.json").read_text(encoding="utf-8"))
    assert users["users"]["admin"]["admin"] is True
    assert users["users"]["admin"]["password_hash"].startswith("$2")


def test_init_refuses_non_empty(init_env):
    rc = cli_main(["init", str(init_env), "--no-git"])
    assert rc == 0
    rc = cli_main(["init", str(init_env), "--no-git"])
    assert rc == 1


def test_init_short_password(monkeypatch, tmp_path):
    monkeypatch.setenv("LIBRY_ADMIN_PASSWORD", "short")
    rc = cli_main(["init", str(tmp_path / "v2"), "--no-git"])
    assert rc == 1


def test_init_then_index(init_env):
    import os
    rc = cli_main(["init", str(init_env), "--no-git"])
    assert rc == 0
    os.chdir(init_env)  # init 后 cwd 即 vault，验证默认 root 推断
    try:
        from libry.config import get_config
        cfg = get_config(refresh=True)
        assert cfg.kb_root == init_env
        from libry.indexer import build_index
        index, _ = build_index(str(init_env))
        assert index["doc_count"] == 3  # Libry + Second Brain + Zettelkasten
    finally:
        os.chdir("/")
