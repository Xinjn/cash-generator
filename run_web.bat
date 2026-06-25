@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

if not exist ".venv" (
    echo 创建虚拟环境...
    python -m venv .venv
)

call .venv\Scripts\activate.bat
pip install -r requirements.txt

python src\web_app.py
