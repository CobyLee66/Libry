#!/usr/bin/env bash
# Libry（书阁）裸机安装：venv + 依赖 + 系统服务（systemd / launchd）。
#
# 用法（在引擎仓库根执行）：
#   bash deploy/install.sh --vault /path/to/vault [--host 0.0.0.0] [--port 8000] [--graph] [--no-service]
#
# 前置：
#   - Python 3.11+
#   - vault 已由 `libry init` 创建（或已有 vault；缺 .env/users.json 时会提示）
#   - Linux 安装 systemd 服务需要 root（sudo）；macOS 装 launchd 服务无需 root
set -euo pipefail

ENGINE="$(cd "$(dirname "$0")/.." && pwd)"
VAULT=""
HOST="127.0.0.1"
PORT="8000"
GRAPH="no"
SERVICE="yes"

while [ $# -gt 0 ]; do
  case "$1" in
    --vault) VAULT="$2"; shift 2 ;;
    --host) HOST="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --graph) GRAPH="yes"; shift ;;
    --no-service) SERVICE="no"; shift ;;
    *) echo "未知参数: $1" >&2; exit 1 ;;
  esac
done

if [ -z "$VAULT" ]; then
  echo "错误：--vault <路径> 必填（指向 libry init 创建的知识库目录）" >&2
  exit 1
fi
VAULT="$(cd "$VAULT" && pwd)"

# ---- 1. Python 版本检查 ----
PY3="$(command -v python3)"
if ! "$PY3" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
  echo "错误：需要 Python 3.11+（当前 $("$PY3" --version)）" >&2
  exit 1
fi

# ---- 2. venv + 依赖 ----
if [ ! -x "$ENGINE/.venv/bin/python" ]; then
  echo "[install] 创建 venv…"
  "$PY3" -m venv "$ENGINE/.venv"
fi
echo "[install] 安装依赖…"
if [ "$GRAPH" = "yes" ]; then
  "$ENGINE/.venv/bin/pip" -q install "$ENGINE[graph]"
else
  "$ENGINE/.venv/bin/pip" -q install "$ENGINE"
fi

BIN="$ENGINE/.venv/bin/libry"
export KB_ROOT="$VAULT"

# ---- 3. vault 完整性检查 ----
if [ ! -d "$VAULT/wiki" ]; then
  echo "错误：$VAULT 不是知识库（缺 wiki/）——先用 libry init 创建" >&2
  exit 1
fi
if [ ! -f "$VAULT/.libry/users.json" ]; then
  echo "[install] 提示：尚无账户，设置 admin 密码："
  KB_ROOT="$VAULT" "$BIN" passwd admin || true
fi

# ---- 4. 系统服务 ----
if [ "$SERVICE" = "no" ]; then
  echo "[install] 跳过服务安装。手动启动：KB_ROOT=$VAULT $BIN serve --host $HOST --port $PORT"
  exit 0
fi

if [ "$(uname -s)" = "Darwin" ]; then
  PLIST="$HOME/Library/LaunchAgents/com.libry.web.plist"
  mkdir -p "$(dirname "$PLIST")"
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.libry.web</string>
  <key>ProgramArguments</key>
  <array>
    <string>$BIN</string>
    <string>serve</string>
    <string>--host</string><string>$HOST</string>
    <string>--port</string><string>$PORT</string>
    <string>--root</string><string>$VAULT</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict><key>KB_ROOT</key><string>$VAULT</string></dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$VAULT/.libry/libry-web.log</string>
  <key>StandardErrorPath</key><string>$VAULT/.libry/libry-web.log</string>
</dict>
</plist>
EOF
  launchctl unload "$PLIST" 2>/dev/null || true
  launchctl load "$PLIST"
  echo "[install] launchd 服务已安装并启动：$PLIST"
  echo "[install] 访问 http://${HOST#0.0.0.0}:$PORT （0.0.0.0 时用本机局域网 IP）"
else
  UNIT=/etc/systemd/system/libry-web.service
  if [ "$(id -u)" != "0" ]; then
    SUDO=sudo
  else
    SUDO=""
  fi
  RUN_USER="${LIBRY_USER:-$(id -un)}"
  $SUDO tee "$UNIT" >/dev/null <<EOF
# 由 Libry install.sh 生成
[Unit]
Description=Libry KB Web (FastAPI/uvicorn)
After=network.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$ENGINE
Environment=KB_ROOT=$VAULT
ExecStart=$BIN serve --host $HOST --port $PORT
Restart=on-failure
RestartSec=3

# 基本加固
NoNewPrivileges=true
ProtectSystem=full
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
  $SUDO systemctl daemon-reload
  $SUDO systemctl enable --now libry-web
  echo "[install] systemd 服务已安装并启动：$UNIT"
  echo "[install] 访问 http://127.0.0.1:$PORT —— 公网暴露建议配 Caddy（deploy/Caddyfile）"
fi
