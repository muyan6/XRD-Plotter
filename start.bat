@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo =======================================================
echo        XRD-Plotter 科研级 XRD 堆叠交互作图工作台
echo =======================================================
echo.
echo 正在启动本地服务并打开浏览器...
echo 本地服务地址: http://127.0.0.1:5000
echo.
echo 提示: 请保持此窗口运行，关闭此窗口服务将停止。
echo.

:: 延迟 1.5 秒后自动打开浏览器
start "" timeout /t 2 /nobreak >nul & start http://127.0.0.1:5000

:: 启动 Flask 服务
python app.py

pause
