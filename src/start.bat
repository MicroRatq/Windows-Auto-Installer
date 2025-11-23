@echo off
chcp 65001 >nul
echo ================================
echo Starting Windows Auto Installer
echo ================================
echo.

cd /d "%~dp0"

:: 检查node_modules
if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
    if %errorlevel% neq 0 (
        echo Error: Failed to install dependencies
        pause
        exit /b 1
    )
)

:: 设置开发环境变量
set NODE_ENV=development

:: 启动Electron
echo Starting Electron...
call npm start

pause


