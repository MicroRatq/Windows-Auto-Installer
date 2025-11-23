@echo off
chcp 65001 >nul
echo ================================
echo Windows自动安装配置项目 - 打包脚本
echo ================================
echo.

set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..
cd /d "%PROJECT_DIR%"

:: 检查必要工具
echo [1/6] 检查打包工具...
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到npm，请先安装Node.js
    pause
    exit /b 1
)

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python
    pause
    exit /b 1
)

where pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo 警告: 未找到PyInstaller，将尝试安装...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo 错误: PyInstaller安装失败
        pause
        exit /b 1
    )
)
echo 工具检查完成
echo.

:: 清理旧的构建文件
echo [2/6] 清理旧的构建文件...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "src\backend\dist" rmdir /s /q "src\backend\dist"
if exist "src\backend\build" rmdir /s /q "src\backend\build"
echo 清理完成
echo.

:: 打包Python后端
echo [3/6] 打包Python后端...
cd src\backend

:: 创建PyInstaller规格文件
echo 创建PyInstaller规格文件...
(
echo # -*- mode: python ; coding: utf-8 -*-
echo.
echo a = Analysis^(
echo     ['main.py'],
echo     pathex=[],
echo     binaries=[],
echo     datas=[],
echo     hiddenimports=['ipc_server', 'iso_handler', 'autounattend', 'migration', 'office_installer', 'activation', 'software_installer'],
echo     hookspath=[],
echo     hooksconfig={},
echo     runtime_hooks=[],
echo     excludes=[],
echo     win_no_prefer_redirects=False,
echo     win_private_assemblies=False,
echo     cipher=block_cipher,
echo     noarchive=False,
echo ^)
echo.
echo pyz = PYZ^(
echo     a.pure,
echo     a.zipped_data,
echo     cipher=block_cipher
echo ^)
echo.
echo exe = EXE^(
echo     pyz,
echo     a.scripts,
echo     a.binaries,
echo     a.zipfiles,
echo     a.datas,
echo     [],
echo     name='backend',
echo     debug=False,
echo     bootloader_ignore_signals=False,
echo     strip=False,
echo     upx=True,
echo     upx_exclude=[],
echo     runtime_tmpdir=None,
echo     console=True,
echo     disable_windowed_traceback=False,
echo     argv_emulation=False,
echo     target_arch=None,
echo     codesign_identity=None,
echo     entitlements_file=None,
echo ^)
) > backend.spec

pyinstaller --clean backend.spec
if %errorlevel% neq 0 (
    echo 错误: Python后端打包失败
    cd ..\..
    pause
    exit /b 1
)

echo Python后端打包完成
cd ..\..
echo.

:: 安装Electron依赖（如果需要）
echo [4/6] 检查Electron依赖...
cd src
if not exist "node_modules" (
    echo 安装Electron依赖...
    call npm install
    if %errorlevel% neq 0 (
        echo 错误: npm install失败
        cd ..
        pause
        exit /b 1
    )
)
cd ..
echo Electron依赖检查完成
echo.

:: 准备打包资源
echo [5/6] 准备打包资源...
if not exist "dist\backend" mkdir "dist\backend"
copy /Y "src\backend\dist\backend.exe" "dist\backend\backend.exe" >nul 2>&1

:: 创建Electron构建配置（如果需要修改）
echo 资源准备完成
echo.

:: 打包Electron应用
echo [6/6] 打包Electron应用...
cd src
call npm run build
if %errorlevel% neq 0 (
    echo 错误: Electron应用打包失败
    cd ..
    pause
    exit /b 1
)
cd ..
echo Electron应用打包完成
echo.

echo ================================
echo 打包完成！
echo ================================
echo.
echo 输出目录: dist\
echo.
echo 提示: 
echo   1. 打包后的应用位于 dist\ 目录
echo   2. 请测试打包后的应用是否正常运行
echo   3. 确保backend.exe在正确的位置
echo.
pause

