#!/bin/bash
# Build Cash Coupon Generator as macOS .app bundle
# Usage: ./build_app.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

APP_NAME="Cash生成器"
APP_BUNDLE="dist/${APP_NAME}.app"

echo "========================================"
echo "Building ${APP_NAME}.app"
echo "========================================"

# Check dependencies
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"
    exit 1
fi

# Ensure PyInstaller is available
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "Installing PyInstaller..."
    pip3 install pyinstaller
fi

# Clean previous build
rm -rf build dist

# Build with PyInstaller using spec file (含体积精简配置)
echo "Running PyInstaller with spec file..."
python3 -m PyInstaller \
    --clean \
    --noconfirm \
    CashCouponGenerator.spec

# spec 文件中的 BUNDLE 已自动生成 ${APP_BUNDLE}，无需手动构造
if [ ! -d "${APP_BUNDLE}" ]; then
    echo "Error: ${APP_BUNDLE} not found after PyInstaller build"
    exit 1
fi

# ==========================================
# 构建后清理：移除空 framework 目录和冗余 platforms 插件
# ==========================================
echo "Post-process: cleaning empty frameworks and unused plugins..."
QT_LIB_DIR="${APP_BUNDLE}/Contents/Frameworks/PyQt5/Qt5/lib"
QT_PLUGINS_DIR="${APP_BUNDLE}/Contents/Frameworks/PyQt5/Qt5/plugins"

# 删除空的 framework 目录（过滤后只剩空壳）
if [ -d "${QT_LIB_DIR}" ]; then
    find "${QT_LIB_DIR}" -type d -name "Qt*.framework" -empty -delete 2>/dev/null || true
    # 再清一遍只含空子目录的 framework
    for fw in "${QT_LIB_DIR}"/Qt*.framework; do
        if [ -d "$fw" ]; then
            real_files=$(find "$fw" -type f ! -name ".*" 2>/dev/null | head -1)
            if [ -z "$real_files" ]; then
                rm -rf "$fw"
            fi
        fi
    done
fi

# 只保留 macOS 需要的 cocoa 平台插件
if [ -d "${QT_PLUGINS_DIR}/platforms" ]; then
    find "${QT_PLUGINS_DIR}/platforms" -type f ! -name "libqcocoa.dylib" -delete 2>/dev/null || true
fi

# 重新签名 bundle
if command -v codesign &> /dev/null; then
    codesign --force --deep --sign - "${APP_BUNDLE}" 2>/dev/null || true
fi

echo "========================================"
echo "Build complete!"
echo "App location: ${APP_BUNDLE}"
echo "App size: $(du -sh "${APP_BUNDLE}" | awk '{print $1}')"
echo ""
echo "To install system-wide:"
echo "  cp -R '${APP_BUNDLE}' /Applications/"
echo "========================================"

# Open dist folder
open "dist" 2>/dev/null || true
