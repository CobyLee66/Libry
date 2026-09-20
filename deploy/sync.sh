#!/usr/bin/env bash
# 【副本端】git pull vault + 按需重建索引。由 cron（兜底）和 /api/sync webhook 共用，
# 幂等，可随时重复执行。引擎代码更新走 update.sh，与本脚本无关。
set -euo pipefail

ENGINE="$(cd "$(dirname "$0")/.." && pwd)"
KB_ROOT="${KB_ROOT:?需要环境变量 KB_ROOT 指向 vault 路径}"
cd "$KB_ROOT"

PY="$ENGINE/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"
LOCAL_URL="${KB_LOCAL_URL:-http://127.0.0.1:8000}"
BRANCH="${KB_GIT_BRANCH:-main}"
LOG_TAG="libry-sync"

CONTENT_DIRS="$("$PY" -c "from libry.config import get_config; print('|'.join(get_config().content_dirs))" 2>/dev/null || true)"
DATA_DIR="$("$PY" -c "from libry.config import get_config; print(get_config().data_dir.name)" 2>/dev/null || echo .libry)"

before=$(git rev-parse HEAD)
git pull --ff-only origin "$(git branch --show-current)" || {
  echo "[$LOG_TAG] git pull 失败（可能存在冲突），需人工处理" >&2
  exit 1
}
after=$(git rev-parse HEAD)

if [ "$before" = "$after" ]; then
  echo "[$LOG_TAG] 无变更，跳过"
  exit 0
fi

# 知识库内容变更时重建索引并热重载
if git diff --name-only "$before" "$after" | grep -qE "^wiki/|^index\.md$|^tags\.md$|^(${CONTENT_DIRS})/"; then
  echo "[$LOG_TAG] 检测到内容变更，重建索引…"
  "$PY" -m libry.indexer "$KB_ROOT"
  if [ -n "${SYNC_SECRET:-}" ]; then
    curl -fsS -X POST "$LOCAL_URL/api/reindex" -H "X-Sync-Secret: $SYNC_SECRET" \
      || echo "[$LOG_TAG] 警告：/api/reindex 调用失败，可重启服务" >&2
  fi
fi

# 拉取到用户数据文件变更时，通知运行中服务热重载
if git diff --name-only "$before" "$after" | grep -qE "^${DATA_DIR}/(users|state|bookmarks|visibility)\.json$"; then
  echo "[$LOG_TAG] 检测到用户数据变更，热重载…"
  if [ -n "${SYNC_SECRET:-}" ]; then
    curl -fsS -X POST "$LOCAL_URL/api/sync-data/reload" -H "X-Sync-Secret: $SYNC_SECRET" \
      || echo "[$LOG_TAG] 警告：/api/sync-data/reload 调用失败，可重启服务" >&2
  fi
fi

echo "[$LOG_TAG] 完成: $before -> $after"
