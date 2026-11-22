@echo off
setlocal
chcp 65001 >nul
title 打卡模块冒烟测试
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0运行冒烟测试.ps1"
set "exitCode=%errorlevel%"
echo.
if "%exitCode%"=="0" (
  echo 冒烟测试通过。
) else (
  echo 冒烟测试未通过，退出码：%exitCode%
)
echo.
echo 按任意键关闭窗口……
pause >nul
exit /b %exitCode%
