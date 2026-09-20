"""Libry 命令行入口。

用法概览（libry --help 看全量）：
    libry init [PATH]          脚手架一个新的知识库 vault（模板 + 密钥 + admin 密码）
    libry serve [--host --port] 启动 Web 服务（读取 vault 根 .env）
    libry index / graph         重建索引 / 关联图
    libry purge [--dry-run]     执行待删除清理
    libry sync-data             多机用户数据同步
    libry passwd [USERNAME]     设置/修改账户密码
    libry config                打印解析后的配置
    libry skills update         从引擎同步最新 agent skills 到 vault
    libry lint                  对 vault 跑全套结构检查
"""
import argparse
import getpass
import json
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from .config import find_root, get_config

PKG_DIR = Path(__file__).resolve().parent
ENGINE_ROOT = PKG_DIR.parent
TEMPLATE_VAULT = PKG_DIR / "templates" / "vault"
# 模板内的可见名 → vault 内的落位名（package_data 对点开头路径不可靠，故模板用普通命名）
TEMPLATE_RENAMES = {"gitignore-template": ".gitignore", "agent-skills": ".agents/skills"}
LINT_TOOLS = ENGINE_ROOT / "tools" / "lint"


def _load_dotenv(path: Path):
    """把 .env（KEY='value' 行）读进 os.environ；已存在的环境变量不覆盖。"""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        line = line.removeprefix("export ").strip()
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


def _write_users(path: Path, username: str, password: str, admin: bool = True):
    import bcrypt
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"users": {username: {
        "password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
        "admin": admin,
    }}}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(path)


# ---------------- 子命令 ----------------

def cmd_init(args) -> int:
    target = Path(args.path or ".").expanduser().resolve()
    if target.exists() and any(target.iterdir()):
        print(f"错误：{target} 非空， refusing 覆盖（换一个空目录或删除内容后重试）", file=sys.stderr)
        return 1
    title = args.title or "我的知识库"

    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(TEMPLATE_VAULT, target, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__"))
    # 点路径落位：gitignore-template → .gitignore，agent-skills → .agents/skills/
    for src_name, dst_rel in TEMPLATE_RENAMES.items():
        src = target / src_name
        if not src.exists():
            continue
        dst = target / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            shutil.rmtree(dst) if dst.is_dir() else dst.unlink()
        shutil.move(str(src), str(dst))
    for d in ("wiki/sources", "wiki/entities", "wiki/concepts", "wiki/synthesis"):
        (target / d).mkdir(parents=True, exist_ok=True)
        keep = target / d / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")

    cfg_file = target / "libry.toml"
    cfg_file.write_text(
        f'# Libry（书阁）知识库配置\n'
        f'title = "{title}"\n\n'
        f'# 顶层内容目录（type=archive 的原文/成品文章，递归收录 .md）。\n'
        f'# 建一个目录加一个名字即可，wiki/ 四个子目录是固定结构。\n'
        f'content_dirs = ["notes"]\n',
        encoding="utf-8")
    (target / "notes").mkdir(exist_ok=True)

    # .env：随机生成会话/webhook 密钥（单机部署即开即用；多机部署见 docs/multi-node-sync.md）
    env_file = target / ".env"
    env_file.write_text(
        f"# Libry 运行密钥（gitignored，勿提交）\n"
        f"SESSION_SECRET='{secrets.token_hex(32)}'\n"
        f"SYNC_SECRET='{secrets.token_hex(32)}'\n"
        f"# HTTPS 环境下设为 'true'（cookie 带 Secure）；本地 http 保持 false\n"
        f"# KB_COOKIE_SECURE='false'\n"
        f"# KB_ROLE='primary'\n",
        encoding="utf-8")
    os.chmod(env_file, 0o600)

    # admin 密码：环境变量（自动化）或交互输入
    password = os.environ.get("LIBRY_ADMIN_PASSWORD", "")
    if not password:
        try:
            password = getpass.getpass("设置 admin 登录密码（至少 8 位）: ")
            confirm = getpass.getpass("再输一次确认: ")
        except EOFError:
            password = confirm = ""
        if password != confirm:
            print("错误：两次输入不一致", file=sys.stderr)
            return 1
    if len(password) < 8:
        print("错误：密码至少 8 位", file=sys.stderr)
        return 1
    _write_users(target / ".libry" / "users.json", "admin", password)

    if not args.no_git:
        r = subprocess.run(["git", "init", "-b", "main"], cwd=str(target),
                           capture_output=True, text=True)
        if r.returncode != 0:  # 老版本 git 不支持 -b
            subprocess.run(["git", "init"], cwd=str(target), capture_output=True)
        print("已初始化 git 仓库（多机同步与发布功能依赖它）")

    print(f"""
知识库已创建：{target}

下一步：
  cd {target}
  libry serve                      # http://127.0.0.1:8000，账户 admin / 你刚设置的密码
  libry skills update              # （可选）日后升级引擎后同步最新 agent skills

让 AI agent（hermes / Claude Code / ZCode 等）维护它：
  在 vault 目录下打开你的 coding agent，它会发现 AGENTS.md 与 .agents/skills/，
  按契约执行入库（ingest）与健康检查（lint）。详见 docs/agent-integration.md。
""")
    return 0


def cmd_serve(args) -> int:
    root = find_root(args.root)
    _load_dotenv(root / ".env")
    os.environ.setdefault("KB_ROOT", str(root))
    import uvicorn
    host = args.host or os.environ.get("KB_HOST", "127.0.0.1")
    port = int(args.port or os.environ.get("KB_PORT", "8000"))
    uvicorn.run("libry.server.main:app", host=host, port=port, proxy_headers=True)
    return 0


def cmd_index(args) -> int:
    from .indexer import build_index
    index, nonstandard = build_index(args.root)
    cfg = get_config(args.root)
    print(f"索引已生成: {cfg.index_path}")
    print(f"条目数: {index['doc_count']}  标准标签: {len(index['standard_tags'])}  "
          f"非标准 tag: {len(nonstandard)} 种")
    return 0


def cmd_graph(args) -> int:
    from .build_graph import main as graph_main
    argv = []
    if args.full:
        argv.append("--full")
    argv += ["--sample", str(args.sample)]
    if args.root:
        argv += ["--root", args.root]
    return graph_main(argv)


def cmd_purge(args) -> int:
    from .purge_marked import run
    report = run(mode_dry_run=args.dry_run, reconcile_only=args.reconcile_only)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


def cmd_sync_data(args) -> int:
    from .sync_data import run as sync_run
    return sync_run(dry_run=args.dry_run)


def cmd_passwd(args) -> int:
    cfg = get_config(args.root)
    username = args.username or "admin"
    password = os.environ.get("LIBRY_PASSWORD", "")
    if not password:
        try:
            password = getpass.getpass(f"设置 {username} 的新密码（至少 8 位）: ")
            confirm = getpass.getpass("再输一次确认: ")
        except EOFError:
            password = confirm = ""
        if password != confirm:
            print("错误：两次输入不一致", file=sys.stderr)
            return 1
    if len(password) < 8:
        print("错误：密码至少 8 位", file=sys.stderr)
        return 1
    _write_users(cfg.data_dir / "users.json", username, password)
    print(f"已写入 {cfg.data_dir / 'users.json'}（运行中的服务重启后生效）")
    return 0


def cmd_config(args) -> int:
    cfg = get_config(args.root)
    print(f"version      {__version__}")
    print(f"engine_root  {ENGINE_ROOT}")
    print(f"kb_root      {cfg.kb_root}")
    print(f"data_dir     {cfg.data_dir}")
    print(f"title        {cfg.title}")
    print(f"content_dirs {cfg.content_dirs}")
    print(f"is_vault     {cfg.is_vault}")
    return 0


def cmd_skills(args) -> int:
    cfg = get_config(args.root)
    src = TEMPLATE_VAULT / "agent-skills"
    dst = cfg.kb_root / ".agents" / "skills"
    if not src.is_dir():
        print(f"错误：模板 skills 不存在（{src}）", file=sys.stderr)
        return 1
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for skill_dir in sorted(src.iterdir()):
        if not skill_dir.is_dir():
            continue
        target = dst / skill_dir.name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(skill_dir, target,
                        ignore=shutil.ignore_patterns("__pycache__"))
        n += 1
        print(f"  已更新 {skill_dir.name}/")
    print(f"已同步 {n} 个 skills 到 {dst}")
    return 0


def cmd_lint(args) -> int:
    cfg = get_config(args.root)
    if not LINT_TOOLS.is_dir():
        print(f"lint 工具不在引擎目录（{LINT_TOOLS}）——pip 安装方式暂不支持，"
              "请用 git clone 安装引擎", file=sys.stderr)
        return 1
    checks = ["lint_wiki.py", "check_dead_links.py", "check_index_strict.py",
              "verify_links.py"]
    env = dict(os.environ)
    env["KB_ROOT"] = str(cfg.kb_root)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    failed = 0
    for name in checks:
        script = LINT_TOOLS / name
        if not script.exists():
            continue
        print(f"\n===== {name} =====")
        r = subprocess.run([sys.executable, str(script), str(cfg.kb_root)], env=env)
        if r.returncode != 0:
            failed += 1
    if failed:
        print(f"\n{failed} 项检查未通过（详见上方输出）")
        return 1
    print("\n全部检查通过")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="libry",
                                 description="Libry（书阁）— AI Agent 维护的个人知识库引擎")
    ap.add_argument("--version", action="version", version=f"libry {__version__}")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="脚手架新知识库 vault")
    p.add_argument("path", nargs="?", default=".", help="目标目录（默认当前目录）")
    p.add_argument("--title", help="知识库标题（写入 libry.toml）")
    p.add_argument("--no-git", action="store_true", help="不初始化 git 仓库")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("serve", help="启动 Web 服务")
    p.add_argument("--host", help="监听地址（默认 KB_HOST 或 127.0.0.1）")
    p.add_argument("--port", type=int, help="端口（默认 KB_PORT 或 8000）")
    p.add_argument("--root", help="vault 根目录（默认 KB_ROOT/cwd）")
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("index", help="重建索引")
    p.add_argument("--root", help="vault 根目录")
    p.set_defaults(func=cmd_index)

    p = sub.add_parser("graph", help="重建关联图（需 libry[graph] 可选依赖）")
    p.add_argument("--full", action="store_true", help="忽略缓存全量重算")
    p.add_argument("--sample", type=int, default=10, help="打印高分关联样例数")
    p.add_argument("--root", help="vault 根目录")
    p.set_defaults(func=cmd_graph)

    p = sub.add_parser("purge", help="执行待删除页面清理")
    p.add_argument("--dry-run", action="store_true", help="只打印执行计划")
    p.add_argument("--reconcile-only", action="store_true", help="只做防复活 reconcile")
    p.set_defaults(func=cmd_purge)

    p = sub.add_parser("sync-data", help="跨端用户数据同步（多机模式）")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_sync_data)

    p = sub.add_parser("passwd", help="设置/修改账户密码")
    p.add_argument("username", nargs="?", default="admin")
    p.add_argument("--root", help="vault 根目录")
    p.set_defaults(func=cmd_passwd)

    p = sub.add_parser("config", help="打印解析后的配置")
    p.add_argument("--root", help="vault 根目录")
    p.set_defaults(func=cmd_config)

    p = sub.add_parser("skills", help="管理 vault 内的 agent skills")
    sub2 = p.add_subparsers(dest="skills_cmd", required=True)
    p2 = sub2.add_parser("update", help="从引擎模板同步最新 skills")
    p2.add_argument("--root", help="vault 根目录")
    p2.set_defaults(func=cmd_skills)

    p = sub.add_parser("lint", help="对 vault 跑全套结构检查")
    p.add_argument("--root", help="vault 根目录")
    p.set_defaults(func=cmd_lint)

    return ap


def main(argv=None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
