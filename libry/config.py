"""Libry 统一配置：全引擎的单一事实来源。

vault 根目录解析顺序（先者胜）：
1. 显式参数（CLI ``--root`` / 函数入参）
2. 环境变量 ``KB_ROOT``
3. 当前工作目录（若它像一个 vault：含 ``libry.toml`` 或 ``wiki/`` 目录）

vault 根的 ``libry.toml``（全部可选）::

    title = "我的知识库"                    # 站点标题（默认 "Libry"）
    content_dirs = ["notes", "clippings"]  # 顶层内容目录（type=archive，递归收录 .md）

环境变量覆盖（优先于 toml）：
- ``KB_ROOT``     vault 根目录
- ``KB_DATA_DIR`` 运行数据目录（默认 ``$KB_ROOT/.libry/``；多机同步模式下须位于 vault 内）
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

WIKI_DIRS = ["sources", "entities", "concepts", "synthesis"]
DATA_DIR_NAME = ".libry"
CONFIG_NAME = "libry.toml"


def _looks_like_vault(p: Path) -> bool:
    return (p / CONFIG_NAME).is_file() or (p / "wiki").is_dir()


def find_root(explicit=None) -> Path:
    """解析 vault 根目录。explicit 为 None 时按 env → cwd 推断。"""
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("KB_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    cwd = Path.cwd().resolve()
    if _looks_like_vault(cwd):
        return cwd
    return cwd  # 非法 vault 也返回 cwd，由调用方给出可读错误


@dataclass
class Config:
    kb_root: Path
    data_dir: Path
    content_dirs: list = field(default_factory=list)
    title: str = "Libry"

    @property
    def index_path(self) -> Path:
        return self.data_dir / "index.json"

    @property
    def content_path(self) -> Path:
        return self.data_dir / "content.json"

    @property
    def graph_path(self) -> Path:
        return self.data_dir / "graph.json"

    @property
    def is_vault(self) -> bool:
        return (self.kb_root / "wiki").is_dir()

    def data_rel(self, name: str) -> str:
        """数据文件相对 vault 根的 POSIX 路径（git 同步用）。数据目录不在 vault 内时抛错。"""
        try:
            rel = self.data_dir.relative_to(self.kb_root)
        except ValueError:
            raise RuntimeError(
                f"KB_DATA_DIR={self.data_dir} 不在 KB_ROOT={self.kb_root} 之内，"
                "多机数据同步要求运行数据随内容仓库走（保持默认 .libry/ 即可）")
        return (rel / name).as_posix()


_cached: Config | None = None
_cached_root: Path | None = None


def get_config(root=None, refresh: bool = False) -> Config:
    """加载配置（按根目录缓存）。测试里可用 refresh=True 或改 env 后重取。"""
    global _cached, _cached_root
    kb_root = find_root(root)
    if _cached is not None and not refresh and _cached_root == kb_root \
            and _cached.data_dir == _resolve_data_dir(kb_root):
        return _cached

    content_dirs: list = []
    title = "Libry"
    toml_path = kb_root / CONFIG_NAME
    if toml_path.is_file():
        if tomllib is None:
            raise RuntimeError("读取 libry.toml 需要 Python 3.11+（tomllib）")
        with open(toml_path, "rb") as fh:
            data = tomllib.load(fh)
        dirs = data.get("content_dirs") or []
        if isinstance(dirs, str):
            dirs = [dirs]
        content_dirs = [str(d).strip("/") for d in dirs if str(d).strip("/")]
        title = str(data.get("title") or "Libry")

    cfg = Config(
        kb_root=kb_root,
        data_dir=_resolve_data_dir(kb_root),
        content_dirs=content_dirs,
        title=title,
    )
    _cached, _cached_root = cfg, kb_root
    return cfg


def _resolve_data_dir(kb_root: Path) -> Path:
    env = os.environ.get("KB_DATA_DIR", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return kb_root / DATA_DIR_NAME
