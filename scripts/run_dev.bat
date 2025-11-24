@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ================================
echo Windows自动安装器 - 开发模式启动
echo ================================
echo.

REM 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
cd /d "%SCRIPT_DIR%\.."

REM 检查conda环境
echo [1/3] 检查Conda环境...
call conda activate win-auto-installer
if %errorlevel% neq 0 (
    echo [错误] 无法激活Conda环境，请先运行 scripts\setup_env.bat
    pause
    exit /b 1
)
echo [成功] Conda环境已激活
echo.

REM 检查前端依赖
echo [2/3] 检查前端依赖...
if not exist "src\frontend\node_modules" (
    echo [信息] 前端依赖未安装，正在安装...
    cd src\frontend
    call npm install
    if %errorlevel% neq 0 (
        echo [错误] npm install失败
        cd ..\..
        pause
        exit /b 1
    )
    cd ..\..
)
echo [成功] 前端依赖已就绪
echo.

REM 启动开发服务器
echo [3/3] 启动开发服务器...
echo.
echo ================================
echo 正在启动 Vite 开发服务器和 Electron...
echo ================================
echo.
echo 提示：
echo - Vite将在 http://localhost:5173 运行
echo - Electron窗口将自动打开
echo - 按 Ctrl+C 停止服务器
echo.

REM 设置环境变量
set NODE_ENV=development

REM 启动Vite和Electron（在后台启动Vite，然后启动Electron）
cd src\frontend
start /B npm run dev
timeout /t 3 /nobreak >nul
call npm run electron:dev
cd ..\..

echo.
echo [信息] 开发服务器已停止
pause

