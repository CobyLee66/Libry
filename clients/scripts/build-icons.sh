#!/bin/bash
# 客户端图标再生成 —— 单一来源：libry/static/icon.png
# 用法: ./scripts/build-icons.sh
#
# 产物：
#   clients/shell/ui/icon.png              壳首启页 + 图标生成源（1024 原图直拷）
#   libry/static/icons/icon-192|512.png    PWA manifest 图标（重采样）
#   clients/shell/src-tauri/icons/         Tauri 全平台图标集（cargo tauri icon，
#                                          含 icns/ico/Android mipmap/iOS AppIcon）
# 任何端的图标变化，只改 libry/static/icon.png 一处，然后重跑本脚本。
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLIENTS_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$CLIENTS_DIR")"
SHELL_DIR="$CLIENTS_DIR/shell"
SRC="$REPO_ROOT/libry/static/icon.png"

echo "🔍 检查图标源..."
if [ ! -f "$SRC" ]; then
    echo "❌ 找不到图标源: $SRC"
    exit 1
fi
# 粗校验尺寸（PNG IHDR）: 宽高须相等（正方形）
SIZE=$(python3 - "$SRC" <<'PY' 2>/dev/null || echo ""
import struct, sys
d = open(sys.argv[1], 'rb').read(33)
w, h = struct.unpack('>II', d[16:24])
print(w if w == h else '')
PY
)
if [ -z "$SIZE" ]; then
    echo "❌ 图标源不是正方形 PNG，请检查 $SRC"
    exit 1
fi
echo "   ✅ 源图标 ${SIZE}x${SIZE} @ $SRC"

echo ""
echo "🎨 Step 1: 同步原图到壳工程（1024 原图直拷，保持最高质量）..."
cp "$SRC" "$SHELL_DIR/ui/icon.png"
echo "   ✅ $SHELL_DIR/ui/icon.png"

echo ""
echo "🎨 Step 2: 生成 PWA manifest 图标（192/512）..."
PWA_DIR="$REPO_ROOT/libry/static/icons"
mkdir -p "$PWA_DIR"
RESIZED=0
if command -v sips >/dev/null 2>&1; then
    sips -z 192 192 "$SRC" --out "$PWA_DIR/icon-192.png" >/dev/null
    sips -z 512 512 "$SRC" --out "$PWA_DIR/icon-512.png" >/dev/null
    RESIZED=1
elif command -v magick >/dev/null 2>&1; then
    magick "$SRC" -resize 192x192 "$PWA_DIR/icon-192.png"
    magick "$SRC" -resize 512x512 "$PWA_DIR/icon-512.png"
    RESIZED=1
elif command -v convert >/dev/null 2>&1; then
    convert "$SRC" -resize 192x192 "$PWA_DIR/icon-192.png"
    convert "$SRC" -resize 512x512 "$PWA_DIR/icon-512.png"
    RESIZED=1
else
    # Pillow 兜底（Libry 是 Python 项目，开发环境通常有 PIL；没有则提示装 magick）
    python3 - "$SRC" "$PWA_DIR" <<'PY'
import sys
try:
    from PIL import Image
except ImportError:
    raise SystemExit("no PIL")
img = Image.open(sys.argv[1])
for s in (192, 512):
    img.resize((s, s), Image.LANCZOS).save(f"{sys.argv[2]}/icon-{s}.png")
PY
    RESIZED=1
fi
if [ "$RESIZED" -eq 1 ]; then
    echo "   ✅ $PWA_DIR/icon-192.png + icon-512.png"
else
    echo "❌ 无可用重采样工具（sips/magick/convert/Pillow 任一）"
    exit 1
fi

echo ""
echo "🎨 Step 3: 生成 Tauri 全平台图标集..."
if cargo tauri --version >/dev/null 2>&1; then
    (cd "$SHELL_DIR/src-tauri" && cargo tauri icon "$SHELL_DIR/ui/icon.png")
    echo "   ✅ $SHELL_DIR/src-tauri/icons/（icns / ico / png / android mipmap / iOS AppIcon）"
else
    echo "⚠️  未找到 tauri-cli，跳过全平台图标集（桌面/移动打包需要它）"
    echo "   修复: cargo install tauri-cli --version 2.12.4 --locked 后重跑本脚本"
fi

echo ""
echo "🎨 Step 4: Android 自适应图标前景层安全区修正..."
# cargo tauri icon 把原图铺满 108dp 前景画布（内容占比 100%），而启动器只显示中央
# 72dp——瓷砖边缘被裁掉约 1/3。这里把原图缩放到画布 66.7%（= 可见区满幅）后居中
# 放到透明前景层上，启动器即可完整呈现原始瓷砖；背景层保持白色。
if python3 -c "import PIL" >/dev/null 2>&1; then
    python3 - "$SRC" "$SHELL_DIR/src-tauri/icons/android" <<'PY'
import pathlib, sys
from PIL import Image
src = Image.open(sys.argv[1]).convert("RGBA")
root = pathlib.Path(sys.argv[2])
DENSITIES = {"mdpi": 108, "hdpi": 162, "xhdpi": 216, "xxhdpi": 324, "xxxhdpi": 432}
RATIO = 2 / 3  # 108dp 画布的可视区 72dp：内容缩到 66.7% 后不再被启动器裁剪
for name, canvas in DENSITIES.items():
    p = root / f"mipmap-{name}" / "ic_launcher_foreground.png"
    if not p.exists():
        continue
    fg = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    size = round(canvas * RATIO)
    off = (canvas - size) // 2
    fg.paste(src.resize((size, size), Image.LANCZOS), (off, off))
    fg.save(p)
    print(f"   ✅ mipmap-{name}/ic_launcher_foreground.png → 内容 {RATIO:.1%} 画布")
PY
else
    echo "❌ 需要 Pillow（python3 -m pip install pillow）——否则安卓启动图标会被裁边"
    exit 1
fi

echo ""
echo "🎉 图标再生成完成 —— 全端统一来自 libry/static/icon.png"
