@echo off
chcp 65001 >nul
echo ========================================
echo NGA狼大发言单次爬取
echo ========================================
echo.
echo 正在执行单次爬取...
echo.

cd /d "%~dp0"
"D:\WindowsApps\PythonSoftwareFoundation.Python.3.9_3.9.3568.0_x64__qbz5n2kfra8p0\python.exe" nga_auto_crawler.py --once

echo.
echo 爬取完成！
pause