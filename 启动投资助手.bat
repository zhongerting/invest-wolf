@echo off
chcp 65001 >nul
title 狼大投资助手
echo ========================================
echo 狼大投资助手 v1.0 正在启动...
echo ========================================
echo.
cd /d "%~dp0"
python main.py
pause