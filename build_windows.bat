@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo  CashGenerator Windows 安装包打包脚本
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+ 并添加到 PATH
    pause
    exit /b 1
)

REM 检查 NSIS
where makensis >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 NSIS，请先安装 NSIS 并添加到 PATH
    echo 下载地址：https://nsis.sourceforge.io/Download
    pause
    exit /b 1
)

REM 创建并激活虚拟环境（可选）
if not exist ".venv_windows" (
    echo [1/6] 创建虚拟环境...
    python -m venv .venv_windows
)

echo [2/6] 激活虚拟环境并安装依赖...
call .venv_windows\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo [3/6] 清理旧构建...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

echo [4/6] 使用 PyInstaller 打包...
pyinstaller --clean --noconfirm CashCouponGenerator_win.spec
if errorlevel 1 (
    echo [错误] PyInstaller 打包失败
    pause
    exit /b 1
)

echo [5/6] 制作 NSIS 安装包...
makensis installer.nsi
if errorlevel 1 (
    echo [错误] NSIS 安装包制作失败
    pause
    exit /b 1
)

echo [6/6] 制作便携版压缩包...
powershell -Command "Compress-Archive -Path 'dist\CashGenerator' -DestinationPath 'dist\CashGenerator_Windows_Portable.zip' -Force"
if errorlevel 1 (
    echo [警告] 便携版压缩包制作失败
)

echo.
echo ========================================
echo  打包完成！
echo ========================================
echo 安装包：dist\CashGenerator_Setup.exe
echo 便携版：dist\CashGenerator_Windows_Portable.zip
echo.
pause
