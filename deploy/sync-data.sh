#!/usr/bin/env bash
# 跨端用户数据同步（两端通用）：拉取 → 语义合并 → 提交推送 → 本机进程热重载。
# 触发方式：每天 cron（见 deploy/cron/），或网页「立即同步」按钮。
set -euo pipefail

ENGINE="$(cd "$(dirname "$0")/.." && pwd)"
KB_ROOT="${KB_ROOT:-$(pwd)}"
cd "$KB_ROOT"

[ -f .env ] && { set -a; . ./.env; set +a; }

PY="$ENGINE/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

exec "$PY" -m libry.sync_data "$@"
