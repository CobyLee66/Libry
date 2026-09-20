#!/usr/bin/env bash
# 定时入库（无人值守）：驱动任意 coding agent 按 AGENTS.md 执行 ingest 流程。
#
# 配置（vault 根 .env 或环境变量）：
#   KB_AGENT_CMD='claude -p "{prompt}"'   # 你的 agent 无头调用模板，{prompt} 为占位符。
#                                         # 例：'hermes run --prompt "{prompt}"' / 'zcode -p "{prompt}"'
#   LIBRY_NOTIFY_WEBHOOK='https://...'    # 可选：结果推送 webhook（notify.sh）
set -euo pipefail

ENGINE="$(cd "$(dirname "$0")/.." && pwd)"
KB_ROOT="${KB_ROOT:-$(pwd)}"
cd "$KB_ROOT"
[ -f .env ] && { set -a; . ./.env; set +a; }

if [ -z "${KB_AGENT_CMD:-}" ]; then
  echo "[run-ingest] 错误：未配置 KB_AGENT_CMD（agent 无头调用模板，见脚本头注释）" >&2
  exit 1
fi

RESULT_FILE="${LIBRY_RESULT_FILE:-/tmp/libry-ingest-result.txt}"

PROMPT="你是知识库的维护 agent。阅读当前目录的 AGENTS.md 并严格按其「入库」流程执行（含第 0 步待删除清理）。检查 pending.md 与 raw/ 中的待入库资料：有则完整入库（含 index.md / wiki/log.md 更新与 libry lint 验证）；没有则报告「无新资料」。把结果摘要写入 $RESULT_FILE。"

echo "[run-ingest] $(date '+%F %T') 启动 agent 入库…"
Q_PROMPT=$(printf '%q' "$PROMPT")
eval " ${KB_AGENT_CMD//\{prompt\}/$Q_PROMPT}" || {
  bash "$ENGINE/scripts/notify.sh" "[libry] 定时入库失败：agent 调用出错，见日志"
  exit 1
}

bash "$ENGINE/scripts/notify.sh" "[libry] 定时入库完成：$(head -c 500 "$RESULT_FILE" 2>/dev/null || echo '结果文件未生成')"
