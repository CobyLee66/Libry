#!/usr/bin/env bash
# 定时 lint（无人值守）：先跑结构检查，有安全类问题让 agent 按 AGENTS.md 修复。
#
# 配置同 run-ingest.sh：KB_AGENT_CMD（仅在有 lint 发现时才需要）+ LIBRY_NOTIFY_WEBHOOK。
set -euo pipefail

ENGINE="$(cd "$(dirname "$0")/.." && pwd)"
KB_ROOT="${KB_ROOT:-$(pwd)}"
cd "$KB_ROOT"
[ -f .env ] && { set -a; . ./.env; set +a; }

PY="$ENGINE/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"
RESULT_FILE="${LIBRY_RESULT_FILE:-/tmp/libry-lint-result.txt}"

echo "[run-lint] $(date '+%F %T') 结构检查…"
if KB_ROOT="$KB_ROOT" "$PY" -m libry.__main__ lint --root "$KB_ROOT" > "$RESULT_FILE" 2>&1; then
  bash "$ENGINE/scripts/notify.sh" "[libry] 定时 lint 通过：$(tail -3 "$RESULT_FILE" | tr '\n' ' ')"
  exit 0
fi

# 有发现：让 agent 修复（未配置 agent 则只报告）
if [ -z "${KB_AGENT_CMD:-}" ]; then
  bash "$ENGINE/scripts/notify.sh" "[libry] 定时 lint 发现问题（未配置 KB_AGENT_CMD，请人工处理）：$(tail -20 "$RESULT_FILE" | tr '\n' ' ')"
  exit 1
fi

PROMPT="你是知识库的维护 agent。结构检查发现问题（见 $RESULT_FILE）。阅读当前目录的 AGENTS.md 与 kb-lint skill：按「默认自动修复安全类、破坏性操作先报告」的策略修复，修完重跑 libry lint 验证归零，把修复摘要写回 $RESULT_FILE 并追加 wiki/log.md lint 条目。"

echo "[run-lint] 发现问题，启动 agent 修复…"
Q_PROMPT=$(printf '%q' "$PROMPT")
eval " ${KB_AGENT_CMD//\{prompt\}/$Q_PROMPT}" || true

bash "$ENGINE/scripts/notify.sh" "[libry] 定时 lint：$(head -c 500 "$RESULT_FILE")"
