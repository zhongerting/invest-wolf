@echo off
chcp 65001 >nul
echo ========================================
echo NGA狼大发言自动爬取工具
echo ========================================
echo.
echo 启动定时任务模式...
echo 盘中爬取: 9:30-11:30, 13:00-15:00 每5分钟
echo 晚间爬取: 23:00
echo 每日备份: 00:00
echo.
echo 按 Ctrl+C 可停止运行
echo ========================================
echo.

cd /d "%~dp0"
"D:\WindowsApps\PythonSoftwareFoundation.Python.3.9_3.9.3568.0_x64__qbz5n2kfra8p0\python.exe" nga_auto_crawler.py --schedule

pause