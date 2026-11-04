@echo off
chcp 65001 > nul
set "PATH=C:\Python311;C:\Python311\Scripts;C:\nodejs;%PATH%"
title He Thong Quan Ly Cong Viec Khoa CNTT - HUIT
echo ===================================================
echo  Khoi chay toan bo He thong (Backend + ML + Frontend)
echo ===================================================
call "%~dp0run_backend.bat"
timeout /t 3 /nobreak > nul
start "Frontend UI (Port 5173)" cmd /k "cd /d %~dp0frontend && set PATH=C:\nodejs;%%PATH%% && npm run dev"
echo.
echo ===================================================
echo He thong dang chay!
echo - Web UI:     http://localhost:5173
echo - Swagger UI: http://localhost:8000/docs
echo - ML Health:  http://localhost:8001/health
echo ===================================================

