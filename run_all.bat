@echo off
chcp 65001 > nul
title He Thong Quan Ly Cong Viec Khoa CNTT - HUIT
echo ===================================================
echo  Khoi chay toan bo He thong: Backend, ML va Frontend
echo ===================================================

echo [1/2] Khoi dong Backend va ML...
call "%~dp0run_backend.bat"

echo [2/2] Khoi dong Frontend UI (Port 5173)...
start "Frontend UI (Port 5173)" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"

echo.
echo ===================================================
echo He thong dang chay!
echo - Web UI:     http://localhost:5173
echo - Swagger UI: http://localhost:8000/docs
echo - ML Health:  http://localhost:8001/health
echo ===================================================
