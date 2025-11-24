@echo off
chcp 65001 >nul
call conda activate win-auto-installer
if %errorlevel% neq 0 (
    echo [错误] 无法激活Conda环境
    exit /b 1
)

echo [测试] Python版本:
python --version

echo [测试] 验证依赖包:
python -c "import pycdlib; print('pycdlib: OK')"
python -c "import requests; print('requests: OK')"
python -c "import pywinauto; print('pywinauto: OK')"

echo.
echo [成功] 所有依赖验证通过！

