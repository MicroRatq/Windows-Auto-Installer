@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "CLEANUP_ON_EXIT=1"

echo ================================
echo Windows Auto Installer - Dev Mode
echo ================================
echo.

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
cd /d "%SCRIPT_DIR%\.."

echo [1/3] Checking Conda environment...
call conda activate win-auto-installer
if %errorlevel% neq 0 (
    echo [ERROR] Cannot activate Conda environment, please run scripts\setup_env.bat first
    pause
    exit /b 1
)
echo [OK] Conda environment activated
echo.

echo [2/3] Checking frontend dependencies...
if not exist "src\frontend\node_modules" (
    echo [INFO] Frontend dependencies not installed, installing...
    cd src\frontend
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] npm install failed
        cd ..\..
        pause
        exit /b 1
    )
    cd ..\..
)
echo [OK] Frontend dependencies ready
echo.

echo [3/3] Starting development server...
echo.
echo ================================
echo Starting Vite dev server and Electron...
echo ================================
echo.
echo Tips:
echo - Vite will run on http://localhost:5173
echo - Electron window will open automatically
echo - Press Ctrl+C to stop server
echo - Make sure Conda environment is activated, Python backend will start automatically
echo.

set NODE_ENV=development

cd src\frontend

echo [INFO] Checking if port 5173 is in use...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING 2^>nul') do (
    echo [INFO] Port 5173 is in use, PID: %%a
    echo [INFO] Closing process...
    taskkill /F /PID %%a >nul 2>&1
    if !errorlevel! equ 0 (
        echo [OK] Process closed
    ) else (
        echo [WARN] Cannot close process, may need admin rights
    )
    timeout /t 2 /nobreak >nul
)

echo [INFO] Starting Vite dev server...
start "Vite Dev Server" cmd /k "npm run dev"
if %errorlevel% neq 0 (
    echo [ERROR] Vite startup failed
    goto :error
)

echo [INFO] Waiting for Vite server to start (5 seconds)...
echo [TIP] If Vite server does not start, check the "Vite Dev Server" window
timeout /t 5 /nobreak >nul

echo [INFO] Starting Electron...
call npm run electron:dev
set ELECTRON_EXIT_CODE=%errorlevel%

:cleanup
echo.
echo [INFO] Cleaning up resources...

echo [INFO] Closing Vite dev server...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)

taskkill /F /FI "WINDOWTITLE eq Vite Dev Server*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq npm*" >nul 2>&1

timeout /t 1 /nobreak >nul

cd ..\..

echo [INFO] Development server stopped
if defined ELECTRON_EXIT_CODE (
    exit /b %ELECTRON_EXIT_CODE%
)
goto :end

:error
echo.
echo [ERROR] Error occurred, cleaning up resources...
call :cleanup
pause
exit /b 1

:end
pause
