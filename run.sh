#!/bin/bash
# Cash Coupon Generator - Quick Launch Script (macOS)
# Usage: ./run.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed."
    exit 1
fi

# Install dependencies if needed
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

# Install/update packages
echo "Checking dependencies..."
pip install -q -r requirements.txt

# Run GUI
echo "Launching Cash Coupon Generator..."

# 记录 Python 子进程 PID，便于优雅关闭
PYTHON_PID=""

# 捕获终止信号：优雅关闭 Python 进程，避免 macOS 崩溃报告弹窗
cleanup() {
    if [ -n "$PYTHON_PID" ] && kill -0 "$PYTHON_PID" 2>/dev/null; then
        kill -TERM "$PYTHON_PID" 2>/dev/null
        wait "$PYTHON_PID" 2>/dev/null
    fi
    exit 0
}
trap cleanup SIGTERM SIGINT SIGQUIT

HOT_RELOAD=0 python3 src/main.py &
PYTHON_PID=$!
wait $PYTHON_PID
