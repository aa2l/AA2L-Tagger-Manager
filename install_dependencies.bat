@echo off
chcp 936 >nul
title 安装 AA2L 打标工具依赖

echo ========================================
echo   正在检查 Python 环境...
echo ========================================
python --version >nul 2>&1
if errorlevel 1 (
    echo 未找到 Python，请先安装 Python 3.8 或更高版本。
    pause
    exit /b
)
echo Python 已安装
python --version

echo.
echo ========================================
echo   正在创建虚拟环境（如果不存在）...
echo ========================================
if not exist "venv\Scripts\python.exe" (
    python -m venv venv
    if errorlevel 1 (
        echo 虚拟环境创建失败。
        pause
        exit /b
    )
    echo 虚拟环境创建成功。
) else (
    echo 虚拟环境已存在。
)

echo.
echo ========================================
echo   正在激活虚拟环境并安装依赖...
echo ========================================
call venv\Scripts\activate.bat

echo ========================================
echo   正在安装基础依赖...
echo ========================================
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo 使用默认源重试...
    pip install -r requirements.txt
)

echo.
echo ========================================
echo   正在安装 ONNX Runtime（CPU 版）...
echo ========================================
pip uninstall onnxruntime onnxruntime-gpu -y >nul 2>&1
pip install onnxruntime -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo ONNX Runtime 安装失败，尝试默认源...
    pip install onnxruntime
)

echo.
echo ========================================
echo   依赖安装完成！
echo   请运行 run.bat 启动程序。
echo ========================================
pause