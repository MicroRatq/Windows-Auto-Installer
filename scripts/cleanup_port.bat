@echo off
chcp 65001 >nul
echo 清理端口5173的占用进程...
echo.

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do (
    echo 发现进程ID: %%a
    taskkill /F /PID %%a >nul 2>&1
    if %errorlevel% equ 0 (
        echo [成功] 已关闭进程 %%a
    ) else (
        echo [失败] 无法关闭进程 %%a，可能需要管理员权限
    )
)

echo.
echo 清理完成
pause

