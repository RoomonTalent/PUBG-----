@echo off
chcp 65001 >nul
echo ========================================
echo   PUBG 迫击炮测距工具 - 打包脚本
echo ========================================
echo.

REM 检查 pyinstaller 是否安装
pyinstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 pyinstaller，请先运行: pip install pyinstaller
    pause
    exit /b 1
)

echo [1/2] 清理旧的构建文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "*.spec" del /q "*.spec"

echo [2/2] 开始打包...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "PUBG测距工具" ^
    --icon="icon.ico" ^
    --add-data "icon.ico;." ^
    --add-data "requirements.txt;." ^
    --hidden-import psutil ^
    --hidden-import tkinter ^
    --hidden-import queue ^
    --hidden-import json ^
    --hidden-import re ^
    --hidden-import winreg ^
    pubg_ranging_tool.py

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo   打包成功！
    echo   输出文件: dist\PUBG测距工具.exe
    echo ========================================
    echo   注意: dist\ 文件夹已被 .gitignore 忽略, 不会上传到 Git
    echo ========================================
) else (
    echo.
    echo [错误] 打包失败，请检查上方错误信息
)

pause
