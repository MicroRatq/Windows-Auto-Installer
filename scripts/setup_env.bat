@echo off
chcp 65001 >nul

:: Get script directory and project root
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "PROJECT_ROOT=%SCRIPT_DIR%\.."
cd /d "%PROJECT_ROOT%"
set "PROJECT_ROOT=%CD%"

echo ================================
echo Windows Auto Installer - Environment Setup
echo ================================
echo Script directory: %SCRIPT_DIR%
echo Project root: %PROJECT_ROOT%
echo.

:: Check Node.js environment
echo [1/5] Check Node.js environment...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Node.js not found, please install Node.js
    echo Download address: https://nodejs.org/
    pause
    exit /b 1
)
node --version
echo Node.js check passed
echo.

:: Check Python environment
echo [2/5] Check Python environment...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python not found, please install Python
    pause
    exit /b 1
)
python --version
echo Python check passed
echo.

:: Check Conda environment
echo [3/5] Check Conda environment...
call conda --version
if %errorlevel% neq 0 (
    echo Error: Conda not found, please install Anaconda or Miniconda
    echo Download address: https://www.anaconda.com/products/distribution
    pause
    exit /b 1
)
echo Conda check passed
echo.

:: Create/activate Conda environment
echo [4/5] Configure Conda environment...
set ENV_NAME=windows-auto-installer

:: Accept Conda Terms of Service if needed
echo Checking Conda Terms of Service...

:: Check if environment exists
conda env list | findstr /C:"%ENV_NAME%" >nul 2>&1
if %errorlevel% neq 0 (
    echo Creating new Conda environment: %ENV_NAME%
    conda create -n %ENV_NAME% -y
    echo Conda environment created successfully
) else (
    echo Conda environment %ENV_NAME% already exists
)
echo.

:: Install Python dependencies
echo [5/5] Install Python dependencies...
echo Note: Installing dependencies in the Conda environment...
call conda activate %ENV_NAME%
set "REQUIREMENTS_FILE=%PROJECT_ROOT%\requirements.txt"
if exist "%REQUIREMENTS_FILE%" (
    echo Installing from: %REQUIREMENTS_FILE%
    pip install -r "%REQUIREMENTS_FILE%"
    if %errorlevel% neq 0 (
        echo Warning: Python dependencies installation may have problems, please check requirements.txt
    ) else (
        echo Python dependencies installation completed
    )
) else (
    echo Warning: requirements.txt not found at %REQUIREMENTS_FILE%, skip Python dependencies installation
)
echo.

:: Check Electron project (if exists)
set "SRC_DIR=%PROJECT_ROOT%\src"
set "PACKAGE_JSON=%SRC_DIR%\package.json"
if exist "%PACKAGE_JSON%" (
    echo Detected Electron project, install Node.js dependencies...
    echo Package.json location: %PACKAGE_JSON%
    cd /d "%SRC_DIR%"
    call npm install
    if %errorlevel% neq 0 (
        echo Warning: Node.js dependencies installation may have problems
    ) else (
        echo Node.js dependencies installation completed
    )
    cd /d "%PROJECT_ROOT%"
    echo.
)

echo ================================
echo Environment configuration completed
echo ================================
echo.
echo Tip: Please use the following command to activate the Conda environment:
echo   conda activate %ENV_NAME%
echo.
pause

