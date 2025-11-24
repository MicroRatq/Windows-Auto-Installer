@echo off
chcp 65001 >nul
echo 测试Vite服务器连接...
echo.

cd src\frontend

echo 启动Vite开发服务器...
start "Vite Dev Server" cmd /k "npm run dev"

echo 等待服务器启动...
timeout /t 5 /nobreak >nul

echo.
echo 测试连接 http://localhost:5173 ...
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:5173' -TimeoutSec 5; Write-Host '成功! 状态码:' $response.StatusCode } catch { Write-Host '失败:' $_.Exception.Message }"

echo.
echo 按任意键关闭Vite服务器...
pause >nul
taskkill /F /FI "WINDOWTITLE eq Vite Dev Server*" >nul 2>&1

