@echo off
chcp 65001 >nul
title Dev Client
cd /d "%~dp0"

python -m develope.dev_client

echo.
echo 🛑 Dev Client 已結束。
pause
