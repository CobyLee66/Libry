#!/usr/bin/env bash
# 【权威端】知识库发布：commit + push 内容变更 + 通知远端 Web 立即拉取。
# 由 agent 在入库（kb-ingest）/修复（kb-lint）完成后调用，也可手动执行。
#
# 配置（vault 根目录 .env，不入库）：KB_WEB_URL、SYNC_SECRET；
# 可选 KB_SSH_HOST（graph.json 直传远端用，须可免密登录远端）。
# 环境变量：KB_ROOT 指定 vault（默认当前目录）。
set -euo pipefail

ENGINE="$(cd "$(dirname "$0")/.." && pwd)"
KB_ROOT="${KB_ROOT:-$(pwd)}"
cd "$KB_ROOT"

if [ -f .env ]; then
  set -a; . ./.env; set +a
fi

PY="$ENGINE/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

CONTENT_DIRS="$("$PY" -c "from libry.config import get_config; print(' '.join(get_config().content_dirs))" 2>/dev/null || true)"
DATA_DIR="$("$PY" -c "from libry.config import get_config; print(get_config().data_dir.name)" 2>/dev/null || echo .libry)"

# 关联图增量重算：内容有变更时本地重建索引 + 重算 graph.json（KB_GRAPH_AUTO='false' 关闭）
# 需要引擎装了 graph 可选依赖；未安装或失败不阻断发布。
# graph.json 是派生数据，不入 git：构建成功后经 SSH 直传远端，远端 /api/reindex 时重载。
GRAPH_BUILT=""
if [ "${KB_GRAPH_AUTO:-true}" != "false" ]; then
  # 触发条件 = wiki 页 + 顶层内容目录（content_dirs，与索引器一致）
  if git status --porcelain -- wiki/ index.md tags.md $CONTENT_DIRS | grep -q .; then
    if "$PY" -c "import fastembed" 2>/dev/null; then
      echo "[libry-publish] 内容变更，重建索引并重算关联图…"
      "$PY" -m libry.indexer "$KB_ROOT"
      if "$PY" -m libry.build_graph --root "$KB_ROOT"; then
        GRAPH_BUILT=1
      else
        echo "[libry-publish] 警告：关联图构建失败，继续发布（图数据保持旧版）" >&2
      fi
    else
      echo "[libry-publish] 提示：未安装 graph 可选依赖，跳过关联图更新" >&2
    fi
  fi
fi

# graph.json 直传远端（须在 webhook 触发对端 reindex 之前到位）
if [ -n "$GRAPH_BUILT" ] && [ -f "$KB_ROOT/$DATA_DIR/graph.json" ] && [ -n "${KB_SSH_HOST:-}" ]; then
  if [ -n "${KB_REMOTE_DATA_DIR:-}" ]; then
    if ssh -o BatchMode=yes -o ConnectTimeout=8 "$KB_SSH_HOST" "cat > '$KB_REMOTE_DATA_DIR/graph.json'" \
        < "$KB_ROOT/$DATA_DIR/graph.json" 2>/dev/null; then
      echo "[libry-publish] graph.json 已直传远端"
    else
      echo "[libry-publish] 警告：graph.json 直传失败，远端沿用旧图" >&2
    fi
  else
    echo "[libry-publish] 提示：未配置 KB_REMOTE_DATA_DIR，跳过 graph 直传" >&2
  fi
fi

# 防复活：对端 purge 删除页面并 push 后，本机 reset --soft 对齐 origin 时
# 工作区/索引会残留已删文件；publish 前先 reconcile 清掉，否则下面 git add 会把它们重新提交
"$PY" -m libry.purge_marked --reconcile-only >/dev/null 2>&1 || true

# 只提交知识库内容变更（引擎代码改动走引擎仓库的 update.sh）
git add wiki/ index.md tags.md $CONTENT_DIRS 2>/dev/null || true

if git diff --cached --quiet; then
  echo "[libry-publish] 无知识库内容变更，跳过 commit/push"
else
  git commit -m "ingest: $(date +%F) 知识库更新"
  if ! git push; then
    echo "[libry-publish] 错误：git push 失败（可能有冲突），请人工 pull --rebase 后重试" >&2
    exit 1
  fi
  echo "[libry-publish] 已推送到远端"
fi

# 通知远端立即 git pull + reindex（失败不阻断，远端 cron 兜底）
if [ -n "${KB_WEB_URL:-}" ] && [ -n "${SYNC_SECRET:-}" ]; then
  if curl -fsS -X POST "$KB_WEB_URL/api/sync" -H "X-Sync-Secret: $SYNC_SECRET" --max-time 15; then
    echo "[libry-publish] 已通知远端同步"
  else
    echo "[libry-publish] 警告：webhook 调用失败，远端将由 cron 兜底拉取" >&2
  fi
else
  echo "[libry-publish] 提示：KB_WEB_URL/SYNC_SECRET 未配置，跳过 webhook（远端 cron 兜底）" >&2
fi
