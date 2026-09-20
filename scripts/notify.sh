#!/usr/bin/env bash
# 通用通知：向 LIBRY_NOTIFY_WEBHOOK POST 一条 JSON {"text": ...}。未配置时打印到 stdout。
#
# 适配示例——QQ 机器人（文档见 docs/agent-integration.md）：
#   LIBRY_NOTIFY_WEBHOOK 指向你自己的转发服务（把 {"text"} 转成 QQ 群消息）；
#   密钥类信息永远走环境变量，绝不写进仓库。
set -euo pipefail

TEXT="${1:-}"
[ -n "$TEXT" ] || exit 0

WEBHOOK="${LIBRY_NOTIFY_WEBHOOK:-}"
if [ -z "$WEBHOOK" ]; then
  echo "[notify] $TEXT"
  exit 0
fi

# jq 不可用时的兜底：python 转义
PAYLOAD="$(python3 -c 'import json,sys; print(json.dumps({"text": sys.argv[1]}))' "$TEXT")"
curl -fsS -X POST "$WEBHOOK" -H 'Content-Type: application/json' -d "$PAYLOAD" --max-time 10 \
  || echo "[notify] 警告：webhook 调用失败" >&2
