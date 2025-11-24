@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ================================
echo Windows自动安装器 - 环境配置脚本
echo ================================
echo.

REM 检查Node.js是否安装
echo [1/5] 检查Node.js...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到Node.js，请先安装Node.js 20 LTS或更高版本
    echo 下载地址: https://nodejs.org/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo [成功] Node.js已安装: %NODE_VERSION%
echo.

REM 检查conda是否安装
echo [2/5] 检查Conda...
where conda >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到Conda，请先安装Anaconda或Miniconda
    echo 下载地址: https://www.anaconda.com/download 或 https://docs.conda.io/en/latest/miniconda.html
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('conda --version') do set CONDA_VERSION=%%i
echo [成功] Conda已安装: %CONDA_VERSION%
echo.

REM 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
cd /d "%SCRIPT_DIR%\.."

REM 检查environment.yml是否存在
if not exist "environment.yml" (
    echo [错误] 未找到environment.yml文件
    pause
    exit /b 1
)

REM 创建conda环境
echo [3/5] 创建Conda环境...
conda env list | findstr /C:"win-auto-installer" >nul 2>&1
if %errorlevel% equ 0 (
    echo [提示] 环境 win-auto-installer 已存在，是否重新创建？(Y/N)
    set /p RECREATE=
    if /i "!RECREATE!"=="Y" (
        echo [信息] 删除现有环境...
        conda env remove -n win-auto-installer -y
        echo [信息] 创建新环境...
        conda env create -f environment.yml
    ) else (
        echo [信息] 使用现有环境，更新依赖...
        conda env update -n win-auto-installer -f environment.yml --prune
    )
) else (
    echo [信息] 创建新环境...
    conda env create -f environment.yml
)
if %errorlevel% neq 0 (
    echo [错误] Conda环境创建失败
    pause
    exit /b 1
)
echo [成功] Conda环境创建完成
echo.

REM 激活conda环境并验证
echo [4/5] 激活Conda环境并验证...
call conda activate win-auto-installer
if %errorlevel% neq 0 (
    echo [错误] 无法激活Conda环境
    pause
    exit /b 1
)

REM 验证Python版本
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] Python未正确安装
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [成功] Python版本: %PYTHON_VERSION%

REM 验证关键依赖
echo [信息] 验证关键依赖...
python -c "import pycdlib; print('pycdlib: OK')" 2>nul
if %errorlevel% neq 0 (
    echo [警告] pycdlib未正确安装
)

python -c "import requests; print('requests: OK')" 2>nul
if %errorlevel% neq 0 (
    echo [警告] requests未正确安装
)

if "%OS%"=="Windows_NT" (
    python -c "import pywinauto; print('pywinauto: OK')" 2>nul
    if %errorlevel% neq 0 (
        echo [警告] pywinauto未正确安装（仅Windows需要）
    )
)
echo.

REM 安装Node.js依赖
echo [5/5] 安装Node.js依赖...
if not exist "src\frontend\package.json" (
    echo [提示] 前端package.json不存在，将在后续步骤中创建
) else (
    cd src\frontend
    call npm install
    if %errorlevel% neq 0 (
        echo [错误] npm install失败
        cd ..\..
        pause
        exit /b 1
    )
    cd ..\..
    echo [成功] Node.js依赖安装完成
)
echo.

echo ================================
echo 环境配置完成！
echo ================================
echo.
echo 下一步：
echo 1. 运行 scripts\run_dev.bat 进行本地测试
echo 2. 或继续完成项目初始化
echo.
pause

