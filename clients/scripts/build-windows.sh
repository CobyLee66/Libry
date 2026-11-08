#!/bin/bash
# Windows 客户端构建脚本（NSIS .exe + MSI）
# 用法: ./scripts/build-windows.sh [--debug] [其他 cargo tauri build 参数]
#   产物复制到 clients/dist/
# 运行位置：Windows 本机的 Git Bash（或任意装有 MSVC 工具链的环境）
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLIENTS_DIR="$(dirname "$SCRIPT_DIR")"
SHELL_DIR="$CLIENTS_DIR/shell"
SRC_TAURI="$SHELL_DIR/src-tauri"
DIST_DIR="$CLIENTS_DIR/dist"

# 操作系统检测（本脚本只支持在 Windows 上跑）
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$(uname -s)" == MINGW* ]]; then
    echo "✅ Git Bash 环境 ($(uname -s))"
else
    echo "❌ 请在 Windows 的 Git Bash 中运行本脚本（macOS 用 build-macos.sh）"
    exit 1
fi

# === Pre-flight 环境检测 ===
echo ""
echo "🔍 Pre-flight 环境检测..."
command -v cargo >/dev/null 2>&1 || { echo "❌ 未找到 cargo（安装 Rust: https://rustup.rs）"; exit 1; }
echo "   ✅ $(cargo --version)"
if ! cargo tauri --version >/dev/null 2>&1; then
    echo "❌ 未找到 tauri-cli"
    echo "   修复: cargo install tauri-cli --version 2.12.4 --locked"
    exit 1
fi
echo "   ✅ $(cargo tauri --version)"
if [ ! -f "$SRC_TAURI/icons/icon.ico" ]; then
    echo "❌ 缺少 $SRC_TAURI/icons/icon.ico —— 先在 macOS/任意机器运行 ./scripts/build-icons.sh 并同步"
    exit 1
fi
echo "   ✅ 图标集就绪（rc.exe 兼容格式由 cargo tauri icon 生成）"

PROFILE="release"
for a in "$@"; do
  [ "$a" = "--debug" ] && PROFILE="debug"
done

echo ""
echo "🔨 Step 1: cargo tauri build（首次构建需编译数分钟）..."
cd "$SRC_TAURI"
cargo tauri build "$@"

echo ""
echo "📦 Step 2: 归位产物..."
mkdir -p "$DIST_DIR"
BUNDLE_DIR="$SRC_TAURI/target/$PROFILE/bundle"
COPIED=0
for f in "$BUNDLE_DIR"/nsis/*.exe "$BUNDLE_DIR"/msi/*.msi; do
    if [ -f "$f" ]; then
        cp "$f" "$DIST_DIR/"
        echo "   ✅ $DIST_DIR/$(basename "$f")"
        COPIED=1
    fi
done
if [ "$COPIED" -eq 0 ]; then
    echo "❌ 未找到产物，请检查上方构建日志"
    exit 1
fi

echo ""
echo "🎉 Windows 构建完成！"
echo "   提示：安装包未签名，首次安装 SmartScreen 会提示「更多信息 → 仍要运行」"
