#!/bin/bash
# macOS 客户端构建脚本（.app + .dmg）
# 用法: ./scripts/build-macos.sh [--target x86_64-apple-darwin] [--debug] [其他 cargo tauri build 参数]
#   默认构建当前架构（Apple Silicon 为 aarch64）；产物复制到 clients/dist/
# 运行位置：macOS 本机（Rust + tauri-cli 已装）
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLIENTS_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$CLIENTS_DIR")"
SHELL_DIR="$CLIENTS_DIR/shell"
SRC_TAURI="$SHELL_DIR/src-tauri"
DIST_DIR="$CLIENTS_DIR/dist"

# === Pre-flight 环境检测 ===
echo "🔍 Pre-flight 环境检测..."
command -v cargo >/dev/null 2>&1 || { echo "❌ 未找到 cargo（安装 Rust: https://rustup.rs）"; exit 1; }
echo "   ✅ $(cargo --version)"
if ! cargo tauri --version >/dev/null 2>&1; then
    echo "❌ 未找到 tauri-cli"
    echo "   修复: cargo install tauri-cli --version 2.12.4 --locked"
    exit 1
fi
echo "   ✅ $(cargo tauri --version)"
if [ ! -f "$SRC_TAURI/icons/icon.icns" ]; then
    echo "❌ 缺少 $SRC_TAURI/icons/icon.icns —— 先运行 ./scripts/build-icons.sh"
    exit 1
fi
echo "   ✅ 图标集就绪"

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
for f in "$BUNDLE_DIR"/dmg/*.dmg; do
    [ -f "$f" ] && cp "$f" "$DIST_DIR/" && echo "   ✅ $DIST_DIR/$(basename "$f")" && COPIED=1
done
for app in "$BUNDLE_DIR"/macos/*.app; do
    [ -d "$app" ] && echo "   ℹ️  .app 包: $app（未压缩复制，可直接运行）" && COPIED=1
done
if [ "$COPIED" -eq 0 ]; then
    echo "❌ 未找到产物，请检查上方构建日志"
    exit 1
fi

echo ""
echo "🎉 macOS 构建完成！"
echo "   提示：安装包未签名，首次打开需右键 → 打开（绕过 Gatekeeper）"
