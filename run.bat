@echo off
chcp 936 >nul
title AA2L 打标工具 - 启动器

echo ==========================================================
echo                      AA2L 打标工具
echo =================本工具为@aa2l个人制作=====================
echo =======如有问题或进行学习交流欢迎访问学社q群:1019353738=====
echo.

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

if not exist "%PROJECT_DIR%venv\Scripts\python.exe" (
    echo 未检测到虚拟环境，正在自动安装依赖（首次运行需要联网）...
    call install_dependencies.bat
    if errorlevel 1 (
        echo 依赖安装失败，请检查网络后重试。
        pause
        exit /b
    )
)

call "%PROJECT_DIR%venv\Scripts\activate.bat"

echo [1/3] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo 未找到 Python，请先安装 Python 3.8 或更高版本。
    pause
    exit /b
)
echo Python 已安装

echo.
echo [2/3] 检查依赖包...
python -c "import gradio, wdtagger, PIL, pandas, pygtrans" >nul 2>&1
if errorlevel 1 (
    echo 虚拟环境中依赖缺失，请重新运行 install_dependencies.bat
    pause
    exit /b
) else (
    echo 依赖已就绪
)

echo.
echo [3/3] 启动 Web 界面...
echo   正在后台启动服务（无窗口，日志写入 service.log）...

:: 后台启动服务（不弹出任何窗口）
start /b "" "%PROJECT_DIR%venv\Scripts\python.exe" my_tagger.py > service.log 2>&1

:: 等待服务监听端口 (最多 30 秒)
set "URL=http://127.0.0.1:7860"
set "TIMEOUT=30"
set "WAIT=0"
echo   等待服务就绪（最多30秒）...
:check_port
ping -n 2 127.0.0.1 >nul
set /a WAIT+=1
if %WAIT% geq %TIMEOUT% (
    echo 启动超时，请手动访问 %URL% 或检查 service.log
    goto :open_browser_once
)
curl -s -o nul -m 1 %URL% >nul 2>&1
if errorlevel 1 goto :check_port

:: 获取监听 7860 端口的 PID
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :7860 ^| findstr LISTENING') do set "SERVICE_PID=%%a"
if defined SERVICE_PID (
    echo %SERVICE_PID% > service.pid
    echo   服务进程 PID: %SERVICE_PID%
) else (
    echo   警告：未能获取服务 PID，关闭服务功能可能不可用
)

echo.
echo 服务已启动！浏览器将自动打开...
:: 只打开一次浏览器
start %URL%
echo 启动器窗口即将自动关闭...
goto :exit

:open_browser_once
start %URL%
echo 如果浏览器未自动打开，请手动访问 %URL%

:exit
:: 延迟1秒后退出，确保日志写入完成
ping -n 2 127.0.0.1 >nul
exit