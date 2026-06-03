@echo off
chcp 65001 >nul
echo ========================================
echo LLM API 配置工具
echo ========================================
echo.
echo 请选择你要使用的 LLM 服务商：
echo.
echo 1. OpenAI GPT（推荐，分析能力最强）
echo 2. 通义千问（阿里云，国内访问快）
echo 3. 智谱 AI（性价比高）
echo 4. 自定义（其他兼容 OpenAI 格式的 API）
echo 5. 跳过配置
echo.
set /p choice="请输入选项 (1-5): "

if "%choice%"=="1" goto config_openai
if "%choice%"=="2" goto config_qwen
if "%choice%"=="3" goto config_glm
if "%choice%"=="4" goto config_custom
if "%choice%"=="5" goto end

:config_openai
echo.
echo 你选择了：OpenAI GPT
set /p api_key="请输入你的 OpenAI API Key: "
set api_url=https://api.openai.com/v1/chat/completions
set model=gpt-4o
goto save_config

:config_qwen
echo.
echo 你选择了：通义千问
set /p api_key="请输入你的阿里云 API Key: "
set api_url=https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
set /p model="请输入模型名称 (默认 qwen-turbo): "
if "%model%"=="" set model=qwen-turbo
goto save_config

:config_glm
echo.
echo 你选择了：智谱 AI
set /p api_key="请输入你的智谱 API Key: "
set api_url=https://open.bigmodel.cn/api/paas/v4/chat/completions
set /p model="请输入模型名称 (默认 glm-3-turbo): "
if "%model%"=="" set model=glm-3-turbo
goto save_config

:config_custom
echo.
echo 你选择了：自定义
set /p api_url="请输入 API 地址: "
set /p api_key="请输入 API Key: "
set /p model="请输入模型名称 (默认 gpt-4o): "
if "%model%"=="" set model=gpt-4o
goto save_config

:save_config
echo.
echo ========================================
echo 配置信息：
echo API 地址：%api_url%
echo API Key: %api_key%
echo 模型：%model%
echo ========================================
echo.
set /p save="是否保存配置？(Y/N): "

if /i "%save%"=="Y" (
    echo.
    echo 正在保存配置...
    echo.
    echo 请选择保存方式：
    echo 1. 仅保存到当前脚本（临时使用）
    echo 2. 保存到系统环境变量（永久生效，需要重启终端）
    echo.
    set /p save_method="请输入选项 (1-2): "
    
    if "%save_method%"=="1" (
        echo.
        echo @echo off > set_env.bat
        echo set LLM_API_URL=%api_url% >> set_env.bat
        echo set LLM_API_KEY=%api_key% >> set_env.bat
        echo set LLM_MODEL=%model% >> set_env.bat
        echo. >> set_env.bat
        echo echo 环境变量已设置（仅当前会话有效） >> set_env.bat
        echo echo 运行：call set_env.bat >> set_env.bat
        echo.
        echo 已生成 set_env.bat 文件
        echo 使用方法：运行 call set_env.bat 即可设置环境变量
        goto test_config
    )
    
    if "%save_method%"=="2" (
        echo.
        echo 正在添加到系统环境变量...
        echo.
        echo 注意：这需要管理员权限，请在弹出的 UAC 窗口中点击"是"
        pause
        setx LLM_API_URL "%api_url%"
        setx LLM_API_KEY "%api_key%"
        setx LLM_MODEL "%model%"
        echo.
        echo 配置已保存到系统环境变量！
        echo 请关闭当前终端并重新打开，配置即可生效。
        goto end
    )
) else (
    echo.
    echo 配置已取消
    goto end
)

:test_config
echo.
echo 是否立即测试配置？
set /p test="输入 Y 测试，其他跳过： "

if /i "%test%"=="Y" (
    echo.
    echo 正在测试配置...
    call set_env.bat
    python llm_client.py
)

:end
echo.
echo ========================================
echo 配置完成！
echo ========================================
echo.
echo 如需手动设置环境变量，请参考：
echo   Windows: 右键"此电脑" → "属性" → "高级系统设置" → "环境变量"
echo   添加以下变量：
echo     LLM_API_URL=你的 API 地址
echo     LLM_API_KEY=你的 API 密钥
echo     LLM_MODEL=模型名称
echo.
pause
