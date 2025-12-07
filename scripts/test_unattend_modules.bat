@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ================================
echo Unattend Generator Module Tests
echo ================================
echo.

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
cd /d "%SCRIPT_DIR%\.."

echo [1/2] Checking Conda environment...
call conda activate win-auto-installer
if %errorlevel% neq 0 (
    echo [ERROR] Cannot activate Conda environment, please run scripts\setup_env.bat first
    pause
    exit /b 1
)
echo [OK] Conda environment activated
echo.

echo [2/2] Running test script...
echo.
python -u scripts\test_unattend_modules.py
set TEST_EXIT_CODE=%errorlevel%

echo.
if %TEST_EXIT_CODE% equ 0 (
    echo [OK] Tests completed successfully
) else (
    echo [ERROR] Tests failed with exit code %TEST_EXIT_CODE%
)

pause
exit /b %TEST_EXIT_CODE%



