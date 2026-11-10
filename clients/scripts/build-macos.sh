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

# 壳内离线阅读器/镜像桥依赖引擎侧 offline.js（单一来源 libry/static，构建时刷新；产物不入库）
UI_LIB_DIR="$SHELL_DIR/ui/lib"
mkdir -p "$UI_LIB_DIR"
cp -f "$REPO_ROOT/libry/static/offline.js" "$UI_LIB_DIR/offline.js"
echo "   ✅ offline.js 已同步（libry/static → ui/lib）"

# 壳内本地模式（断网时的完整 Web 应用快照）：拷贝 libry/static → ui/webapp/，
# 并在 app.js 之前注入 local-mode.js（fetch 垫片，仅壳内 tauri origin 激活）
WEBAPP_DIR="$SHELL_DIR/ui/webapp"
rm -rf "$WEBAPP_DIR"
mkdir -p "$WEBAPP_DIR"
cp -R "$REPO_ROOT/libry/static/." "$WEBAPP_DIR/"
# awk 跨平台注入（POSIX sed 的 & 与 \& 语义易混，awk 更稳）：
# 在 offline.js 之后、app.js 之前加载垫片（垫片在任何 fetch 调用前完成劫持即可）
awk '{ print } /<script src="offline.js"><\/script>/ { print "<script src=\"local-mode.js\"></script>" }' \
  "$WEBAPP_DIR/index.html" > "$WEBAPP_DIR/index.html.new" && mv "$WEBAPP_DIR/index.html.new" "$WEBAPP_DIR/index.html"
echo "   ✅ Web 应用快照已同步（libry/static → ui/webapp，本地模式垫片已注入）"

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
