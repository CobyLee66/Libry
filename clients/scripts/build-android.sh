#!/bin/bash
# Android APK 构建脚本（Tauri 2 壳：Rust 交叉编译 + Gradle + zipalign + 签名）
# 用法: ./scripts/build-android.sh [--no-install] [--device <serial>]
#   默认构建 release 通用包（4 ABI）、签名、并自动安装到第一个已连接设备；
#   --no-install        只构建不安装
#   --device <serial>   指定 adb 设备序列号
#   产物复制到 clients/dist/Libry_<version>_universal.apk
#
# 运行位置：装了 Android SDK/NDK 的机器（Windows 用 Git Bash，或 Linux/macOS）。
# 安全区适配：构建前会把 android-custom/MainActivity.kt 覆盖到生成的工程——
# gen/ 是生成目录（gitignored），重新 init 后必须重打补丁，本脚本自动处理。
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLIENTS_DIR="$(dirname "$SCRIPT_DIR")"
SHELL_DIR="$CLIENTS_DIR/shell"
SRC_TAURI="$SHELL_DIR/src-tauri"
DIST_DIR="$CLIENTS_DIR/dist"

# 操作系统检测 + 环境变量默认值（用户已设的 JAVA_HOME/ANDROID_HOME/NDK_HOME 优先）
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$(uname -s)" == MINGW* ]]; then
    OS_FAMILY="windows"
    DEFAULT_JAVA_HOME="C:\\Softwares\\Android\\jdk-21.0.5+11"
    DEFAULT_ANDROID_HOME="C:\\Softwares\\Android"
else
    OS_FAMILY="unix"
    DEFAULT_JAVA_HOME="${JAVA_HOME:-}"   # macOS/Linux 无统一默认，未设时 preflight 给出提示
    DEFAULT_ANDROID_HOME="$HOME/Library/Android/sdk"
    [ -d "$DEFAULT_ANDROID_HOME" ] || DEFAULT_ANDROID_HOME="$HOME/Android/Sdk"
fi
export JAVA_HOME="${JAVA_HOME:-$DEFAULT_JAVA_HOME}"
export ANDROID_HOME="${ANDROID_HOME:-$DEFAULT_ANDROID_HOME}"
export ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-$ANDROID_HOME}"
# NDK 默认取 $ANDROID_HOME/ndk 下最新版本
if [ -z "$NDK_HOME" ]; then
    NEWEST_NDK=$(ls "$ANDROID_HOME/ndk" 2>/dev/null | sort -V | tail -1)
    NDK_HOME="${NEWEST_NDK:+$ANDROID_HOME/ndk/$NEWEST_NDK}"
fi
export NDK_HOME
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/build-tools/*:$PATH"

# 签名密钥（不在仓库内；缺失时自动生成新密钥，升级签名必须保持一致）
KEYSTORE="${LIBRY_KEYSTORE:-$SHELL_DIR/keystore/libry-release.keystore}"
KEY_ALIAS="${LIBRY_KEY_ALIAS:-libry}"
KS_PASS="${LIBRY_KEYSTORE_PASS:-libry-sign-2026}"
PKG_ID="com.libry.shell"

# === Pre-flight 环境检测 ===
echo "🔍 Pre-flight 环境检测..."

if [ ! -d "$JAVA_HOME" ] || ! "$JAVA_HOME/bin/java" -version >/dev/null 2>&1; then
    echo "❌ JAVA_HOME 不可用: $JAVA_HOME"
    echo "   修复: export JAVA_HOME=<JDK17+ 目录>（Windows 默认 C:\\Softwares\\Android\\jdk-21.0.5+11）"
    exit 1
fi
JAVA_MAJOR=$("$JAVA_HOME/bin/java" -version 2>&1 | sed -n 's/.*version "\([0-9]*\).*/\1/p' | head -1)
echo "   ✅ JDK $JAVA_MAJOR @ $JAVA_HOME"

if [ ! -d "$ANDROID_HOME" ]; then
    echo "❌ ANDROID_HOME 目录不存在: $ANDROID_HOME"
    echo "   修复: export ANDROID_HOME=<Android SDK 根目录>"
    exit 1
fi
echo "   ✅ Android SDK @ $ANDROID_HOME"

if [ ! -f "$NDK_HOME/source.properties" ]; then
    echo "❌ NDK_HOME 不可用: $NDK_HOME"
    echo "   修复: export NDK_HOME=<NDK 目录>（如 $ANDROID_HOME/ndk/<版本号>）"
    exit 1
fi
echo "   ✅ NDK @ $NDK_HOME"

command -v cargo >/dev/null 2>&1 || { echo "❌ 未找到 cargo"; exit 1; }
echo "   ✅ $(cargo --version)"
if ! cargo tauri --version >/dev/null 2>&1; then
    echo "❌ 未找到 tauri-cli —— 修复: cargo install tauri-cli --version 2.12.4 --locked"
    exit 1
fi

echo "   ⏳ 检查 Android Rust 交叉编译目标..."
MISSING_TARGETS=0
for t in aarch64-linux-android armv7-linux-androideabi i686-linux-android x86_64-linux-android; do
    rustup target list --installed 2>/dev/null | grep -qx "$t" || MISSING_TARGETS=1
done
if [ "$MISSING_TARGETS" -eq 1 ]; then
    echo "   ⏳ 自动补装 rustup target..."
    rustup target add aarch64-linux-android armv7-linux-androideabi i686-linux-android x86_64-linux-android
fi
echo "   ✅ Android 交叉编译目标齐备"

if [ ! -f "$SRC_TAURI/icons/android/mipmap-anydpi-v26/ic_launcher.xml" ]; then
    echo "❌ 缺少 Android 图标集 —— 先运行 ./scripts/build-icons.sh"
    exit 1
fi
echo "   ✅ 图标集就绪"

# 签名密钥：缺失时自动生成（提示备份）
mkdir -p "$(dirname "$KEYSTORE")"
if [ ! -f "$KEYSTORE" ]; then
    echo "   ⏳ 未找到签名密钥，自动生成: $KEYSTORE"
    "$JAVA_HOME/bin/keytool" -genkeypair -keystore "$KEYSTORE" -alias "$KEY_ALIAS" \
        -keyalg RSA -keysize 2048 -validity 10000 \
        -storepass "$KS_PASS" -keypass "$KS_PASS" \
        -dname "CN=Libry Shell, O=Libry, C=CN" >/dev/null 2>&1
    echo "   ⚠️  新密钥已生成 —— 请立即备份 $KEYSTORE（密码 LIBRY_KEYSTORE_PASS，默认 libry-sign-2026）；"
    echo "      升级覆盖安装必须使用同一密钥"
fi
echo "   ✅ 签名密钥 @ $KEYSTORE"

# 解析参数
NO_INSTALL=0
TARGET_DEVICE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-install) NO_INSTALL=1; shift ;;
    --device) TARGET_DEVICE="$2"; shift 2 ;;
    *) echo "未知参数: $1"; exit 1 ;;
  esac
done

# === Step 1: 生成/补丁 Android 工程 ===
echo ""
echo "🤖 Step 1: 准备 Android 工程（gen/ 为生成目录，不入库）..."
if [ ! -f "$SRC_TAURI/gen/android/gradlew.bat" ] && [ ! -f "$SRC_TAURI/gen/android/gradlew" ]; then
    (cd "$SRC_TAURI" && cargo tauri android init)
    echo "   ✅ cargo tauri android init 完成"
fi
# 安全区补丁：覆盖 MainActivity（enableEdgeToEdge 之后按系统栏/刘海/键盘 insets 给 WebView 让位）
cp "$CLIENTS_DIR/android-custom/MainActivity.kt" \
   "$SRC_TAURI/gen/android/app/src/main/java/com/libry/shell/MainActivity.kt"
echo "   ✅ 安全区补丁已应用（android-custom/MainActivity.kt）"
# 图标同步：gen/ 的 res 图标只在首次 init 时拷入，之后图标再更新不会自动跟进——
# 每次构建前把 src-tauri/icons/android/ 覆盖进 gen 工程，保证启动图标始终跟随单一来源
ICONS_ANDROID="$SRC_TAURI/icons/android"
GEN_RES="$SRC_TAURI/gen/android/app/src/main/res"
if [ -d "$ICONS_ANDROID" ]; then
    for d in "$ICONS_ANDROID"/*/; do
        name=$(basename "$d")
        case "$name" in
            mipmap-*|drawable-*|values*) # values 含不带连字符的 values/（ic_launcher_background 色值在此）
                mkdir -p "$GEN_RES/$name"
                cp -f "$d"* "$GEN_RES/$name/" 2>/dev/null || true
                ;;
        esac
    done
    echo "   ✅ 启动图标已同步（icons/android → gen res，单一来源 libry/static/icon.png）"
fi

# 壳内离线阅读器/镜像桥依赖引擎侧 offline.js（单一来源 libry/static，构建时刷新；产物不入库）
UI_LIB_DIR="$SHELL_DIR/ui/lib"
mkdir -p "$UI_LIB_DIR"
cp -f "$CLIENTS_DIR/../libry/static/offline.js" "$UI_LIB_DIR/offline.js"
echo "   ✅ offline.js 已同步（libry/static → ui/lib）"

# === Step 2: 构建 APK ===
echo ""
echo "🔨 Step 2: cargo tauri android build --apk（首次需下载 Gradle 依赖）..."
cd "$SRC_TAURI"
cargo tauri android build --apk

APK_UNSIGNED=$(find gen/android/app/build/outputs/apk/universal/release -name "*-unsigned.apk" | head -1)
if [ -z "$APK_UNSIGNED" ] || [ ! -f "$APK_UNSIGNED" ]; then
    echo "❌ 未找到构建产物（universal release APK）"
    exit 1
fi

# === Step 3: zipalign + 签名 ===
echo ""
echo "🔐 Step 3: zipalign + apksigner 签名..."
BUILD_TOOLS_VER=$(ls "$ANDROID_HOME/build-tools" 2>/dev/null | sort -V | tail -1)
BT="$ANDROID_HOME/build-tools/$BUILD_TOOLS_VER"
# apksigner 在 build-tools 里是 .bat 批处理（无 .exe），Windows/Git Bash 必须带后缀调用
APKSIGNER="$BT/apksigner"
[ "$OS_FAMILY" = "windows" ] && APKSIGNER="$BT/apksigner.bat"
VERSION=$(sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' "$SRC_TAURI/tauri.conf.json" | head -1)
mkdir -p "$DIST_DIR"
SIGNED="$DIST_DIR/Libry_${VERSION}_universal.apk"
"$BT/zipalign" -f -p 4 "$APK_UNSIGNED" "$DIST_DIR/app-universal-aligned.apk"
"$APKSIGNER" sign --ks "$KEYSTORE" --ks-key-alias "$KEY_ALIAS" \
    --ks-pass "pass:$KS_PASS" --key-pass "pass:$KS_PASS" \
    --out "$SIGNED" "$DIST_DIR/app-universal-aligned.apk"
rm -f "$DIST_DIR/app-universal-aligned.apk"
"$APKSIGNER" verify "$SIGNED" && echo "   ✅ 签名校验通过"
SIZE=$(du -h "$SIGNED" | cut -f1)
echo "   ✅ $SIGNED ($SIZE)"

# === Step 4: 自动安装（可 --no-install 跳过） ===
if [ "$NO_INSTALL" -eq 1 ]; then
    echo ""
    echo "ℹ️  已跳过安装（--no-install）。需要时运行: ./scripts/install-apk.sh"
    exit 0
fi

echo ""
echo "📲 Step 4: 检测 ADB 设备..."
DEVICE_LIST=$(adb devices 2>/dev/null | grep -v "^List\|^$" || true)
if [ -z "$DEVICE_LIST" ]; then
    echo "ℹ️  未检测到设备，跳过自动安装。连接手机后运行: ./scripts/install-apk.sh"
    exit 0
fi
if [ -z "$TARGET_DEVICE" ]; then
    TARGET_DEVICE=$(echo "$DEVICE_LIST" | awk '/device$/{print $1; exit}')
fi
if [ -z "$TARGET_DEVICE" ]; then
    echo "❌ 没有处于 device 状态的设备（可能 unauthorized）"
    adb devices
    exit 1
fi
echo "   🎯 目标设备: $TARGET_DEVICE"
if adb -s "$TARGET_DEVICE" install -r "$SIGNED"; then
    echo ""
    echo "🎉 APK 构建并安装完成！启动方式：手机桌面 Libry 图标"
else
    echo ""
    echo "⚠️  安装失败（可能是签名不匹配），尝试卸载后重装..."
    adb -s "$TARGET_DEVICE" uninstall "$PKG_ID" 2>/dev/null || true
    adb -s "$TARGET_DEVICE" install "$SIGNED" && echo "🎉 重装完成！"
fi
