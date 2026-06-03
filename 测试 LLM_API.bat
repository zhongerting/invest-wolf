@echo off
chcp 65001 >nul
echo ========================================
echo LLM API 快速测试脚本
echo ========================================
echo.
echo 这个脚本用于演示如何临时设置环境变量并测试 LLM API
echo.
echo 使用方法：
echo 1. 运行此脚本
echo 2. 输入你的 API 配置
echo 3. 立即测试 LLM 功能
echo.
pause

set /p api_url="请输入 LLM API 地址 (例如 https://api.openai.com/v1/chat/completions): "
set /p api_key="请输入 API Key: "
set /p model="请输入模型名称 (例如 gpt-4o, 回车使用默认): "
if "%model%"=="" set model=gpt-4o

echo.
echo ========================================
echo 配置信息：
echo API 地址：%api_url%
echo 模型：%model%
echo ========================================
echo.
echo 正在设置临时环境变量并测试...
echo.

set LLM_API_URL=%api_url%
set LLM_API_KEY=%api_key%
set LLM_MODEL=%model%

python llm_client.py

echo.
echo ========================================
echo 测试完成！
echo ========================================
echo.
echo 注意：刚才设置的环境变量仅在当前终端会话有效
echo 如需永久配置，请运行：配置 LLM_API.bat
echo 或手动添加到系统环境变量
echo.
pause
