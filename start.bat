@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo =======================================================
echo        XRD-Plotter 科研级 XRD 堆叠交互作图工作台
echo =======================================================
echo.

:: 1. 检测本地 Python 环境
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未在系统中检测到 Python！
    echo ---------------------------------------------------
    echo 运行本工具需要 Python 3.8 或更高版本。
    echo 请前往官网下载安装：https://www.python.org/downloads/
    echo 安装时请务必勾选 "Add python.exe to PATH"（添加环境变量）。
    echo ---------------------------------------------------
    echo.
    pause
    exit /b
)

:: 2. 检查必要科学计算与 Web 依赖，若缺失则自动通过国内镜像源极速安装
python -c "import flask, numpy, scipy, matplotlib" >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] 正在自动检测并安装缺失的科学依赖 (Flask, numpy, scipy, matplotlib)...
    echo 使用清华大学 PyPI 镜像源极速下载，只需首次启动时配置一次...
    echo.
    python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if %errorlevel% neq 0 (
        echo.
        echo [错误] 依赖安装遇到问题，请检查网络或使用 pip 手动安装。
        pause
        exit /b
    )
    echo.
    echo [完成] 运行环境已准备就绪！
    echo.
)

echo 正在启动本地服务并打开浏览器...
echo 本地服务地址: http://127.0.0.1:5000
echo.
echo 提示: 请保持此窗口运行，关闭此窗口服务将停止。
echo.

:: 后台延迟 1.5 秒自动弹出浏览器打开主页
start "" powershell -WindowStyle Hidden -Command "Start-Sleep -Milliseconds 1500; Start-Process 'http://127.0.0.1:5000'"

:: 启动 Flask 服务
python app.py

pause

