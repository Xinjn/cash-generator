#!/bin/bash
# 启动网页版现金券生成器
# 启动后浏览器访问 http://localhost:8080

set -e

cd "$(dirname "$0")"
source .venv/bin/activate
python src/web_app.py
