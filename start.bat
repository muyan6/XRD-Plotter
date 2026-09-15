@echo off
chcp 65001 >nul
cd /d "%~dp0"
title XRD-Plotter

REM 1. 检查 Python 环境是否存在
python --version >nul 2>&1
if errorlevel 1 goto NO_PYTHON

REM 2. 检查 4 个必要科学计算依赖是否存在
python -c "import flask, numpy, scipy, matplotlib" >nul 2>&1
if errorlevel 1 goto INSTALL_DEPS

goto LAUNCH

:INSTALL_DEPS
echo -------------------------------------------------------
echo [提示] 检测到缺少必要科学依赖库，正在自动极速安装...
echo 正在连接清华大学 PyPI 镜像源下载 Flask, numpy, scipy, matplotlib
echo -------------------------------------------------------
echo.
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 goto INSTALL_FAIL
echo.
echo [完成] 所有依赖安装成功！
echo.
goto LAUNCH

:LAUNCH
echo =======================================================
echo        XRD-Plotter 科研级 XRD 堆叠交互作图工作台
echo =======================================================
echo.
echo 正在启动本地服务并打开浏览器...
echo 本地服务地址: http://127.0.0.1:5000
echo.
echo 提示: 请保持此窗口运行，关闭此窗口服务将停止。
echo.
python app.py
goto END

:INSTALL_FAIL
echo.
echo =======================================================
echo [错误] 依赖安装遇到问题，请检查网络后手动执行:
echo python -m pip install -r requirements.txt
echo =======================================================
echo.
pause
goto END

:NO_PYTHON
echo =======================================================
echo [错误] 未在系统中检测到 Python！
echo -------------------------------------------------------
echo 运行本工具需要 Python 3.8 或更高版本。
echo 请前往官网下载安装: https://www.python.org/downloads/
echo 安装时请务必勾选 "Add python.exe to PATH"（添加环境变量）。
echo =======================================================
echo.
pause
goto END

:END
