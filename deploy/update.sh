#!/usr/bin/env bash
# 【两端通用】引擎升级：pull 引擎仓库 → 重装依赖（有变更时）→ 重启服务（在运行的话）。
# 用法：bash deploy/update.sh
set -euo pipefail

ENGINE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ENGINE"

echo "[libry-update] 拉取引擎最新代码…"
git pull --ff-only

if git diff --name-only HEAD@{1} HEAD 2>/dev/null | grep -qE '^(pyproject\.toml|requirements.*)'; then
  echo "[libry-update] 依赖变更，重装…"
  .venv/bin/pip install -U . ${LIBRY_INSTALL_EXTRA:-}
else
  echo "[libry-update] 依赖无变更，跳过安装"
fi

# 重启在运行的服务（尽力而为）
if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet libry-web 2>/dev/null; then
  sudo systemctl restart libry-web
  echo "[libry-update] 已重启 systemd 服务 libry-web"
elif command -v launchctl >/dev/null 2>&1 && launchctl list 2>/dev/null | grep -q com.libry.web; then
  launchctl kickstart -k "gui/$(id -u)/com.libry.web"
  echo "[libry-update] 已重启 launchd 服务 com.libry.web"
else
  echo "[libry-update] 未检测到运行中的服务（手动启动的场景请自行重启）"
fi
echo "[libry-update] 完成"
