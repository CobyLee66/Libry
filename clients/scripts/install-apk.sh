#!/bin/bash
# Android APK 安装脚本（安装已签名的构建产物到 adb 设备）
# 用法: ./scripts/install-apk.sh [--device <serial>] [--apk <path>] [--launch]
#   默认安装 clients/dist/ 下最新的 Libry_*_universal.apk 到第一个可用设备
#   --device <serial>  指定设备序列号（USB 或 adb connect 无线）
#   --apk <path>       指定 APK 路径（默认自动选 dist 最新）
#   --launch           安装后直接启动应用
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLIENTS_DIR="$(dirname "$SCRIPT_DIR")"
DIST_DIR="$CLIENTS_DIR/dist"
PKG_ID="com.libry.shell"

# adb 位置：ANDROID_HOME/platform-tools 优先，系统 PATH 兜底
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$(uname -s)" == MINGW* ]]; then
    DEFAULT_ANDROID_HOME="C:\\Softwares\\Android"
else
    DEFAULT_ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
fi
export ANDROID_HOME="${ANDROID_HOME:-$DEFAULT_ANDROID_HOME}"
export PATH="$ANDROID_HOME/platform-tools:$PATH"

# 解析参数
TARGET_DEVICE=""
APK_PATH=""
LAUNCH=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --device) TARGET_DEVICE="$2"; shift 2 ;;
    --apk) APK_PATH="$2"; shift 2 ;;
    --launch) LAUNCH=1; shift ;;
    *) shift ;;
  esac
done

echo "📱 Step 1: 检查 ADB 设备..."
if ! command -v adb >/dev/null 2>&1; then
    echo "❌ 未找到 adb（检查 ANDROID_HOME/platform-tools）: ANDROID_HOME=$ANDROID_HOME"
    exit 1
fi
DEVICE_LIST=$(adb devices 2>/dev/null | grep -v "^List\|^$" || true)
if [ -z "$DEVICE_LIST" ]; then
    echo "❌ 没有检测到已连接的设备，请检查："
    echo "   1. 手机是否通过 USB 连接（或已 adb connect <ip:端口> 无线连接）"
    echo "   2. 手机是否开启了开发者模式 + USB 调试"
    echo "   3. 手机上是否点了「允许 USB 调试」"
    exit 1
fi
echo "✅ 检测到设备："
echo "$DEVICE_LIST"

if [ -z "$TARGET_DEVICE" ]; then
    TARGET_DEVICE=$(echo "$DEVICE_LIST" | awk '/device$/{print $1; exit}')
fi
if [ -z "$TARGET_DEVICE" ]; then
    echo "❌ 没有处于 device 状态的设备（可能 unauthorized）"
    adb devices
    exit 1
fi
echo "🎯 目标设备: $TARGET_DEVICE"

echo ""
echo "📦 Step 2: 确定 APK..."
if [ -z "$APK_PATH" ]; then
    APK_PATH=$(ls -t "$DIST_DIR"/Libry_*_universal.apk 2>/dev/null | head -1)
fi
if [ -z "$APK_PATH" ] || [ ! -f "$APK_PATH" ]; then
    echo "❌ 未找到可安装的 APK（$DIST_DIR/Libry_*_universal.apk）"
    echo "   请先运行: ./scripts/build-android.sh --no-install"
    exit 1
fi
SIZE=$(du -h "$APK_PATH" | cut -f1)
echo "✅ $APK_PATH ($SIZE)"

echo ""
echo "📲 Step 3: 安装到设备 ($TARGET_DEVICE)..."
if adb -s "$TARGET_DEVICE" install -r "$APK_PATH"; then
    echo "✅ 安装成功"
else
    echo ""
    echo "⚠️  安装失败（可能是签名不匹配，之前装过其他密钥签名的版本）"
    echo "   尝试卸载后重装（会清除应用内已连接的服务器地址等本地数据）..."
    adb -s "$TARGET_DEVICE" uninstall "$PKG_ID" 2>/dev/null || true
    adb -s "$TARGET_DEVICE" install "$APK_PATH"
    echo "✅ 重装成功"
fi

if [ "$LAUNCH" -eq 1 ]; then
    echo ""
    echo "🚀 启动应用..."
    adb -s "$TARGET_DEVICE" shell am start -n "$PKG_ID/.MainActivity"
fi

echo ""
echo "🎉 安装完成！"
