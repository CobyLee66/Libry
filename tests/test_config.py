"""config 解析：root 推断、toml 读取、数据目录相对路径。"""
import pytest

from libry.config import find_root, get_config


def test_explicit_root_wins(vault, env_clean):
    assert find_root(str(vault)) == vault


def test_env_root(vault, env_clean, monkeypatch):
    monkeypatch.setenv("KB_ROOT", str(vault))
    assert find_root() == vault


def test_toml_fields(vault, env_clean):
    cfg = get_config(str(vault), refresh=True)
    assert cfg.title == "测试库"
    assert cfg.content_dirs == ["notes"]
    assert cfg.data_dir == vault / ".libry"
    assert cfg.is_vault
    assert cfg.data_rel("users.json") == ".libry/users.json"


def test_missing_toml_defaults(tmp_path, env_clean):
    (tmp_path / "wiki").mkdir()
    cfg = get_config(str(tmp_path), refresh=True)
    assert cfg.title == "Libry"
    assert cfg.content_dirs == []


def test_data_rel_outside_vault(tmp_path, env_clean, monkeypatch):
    (tmp_path / "wiki").mkdir()
    monkeypatch.setenv("KB_DATA_DIR", str(tmp_path.parent / "elsewhere"))
    cfg = get_config(str(tmp_path), refresh=True)
    with pytest.raises(RuntimeError):
        cfg.data_rel("users.json")


def test_index_paths(vault, env_clean):
    cfg = get_config(str(vault), refresh=True)
    assert cfg.index_path == vault / ".libry" / "index.json"
    assert cfg.graph_path == vault / ".libry" / "graph.json"
