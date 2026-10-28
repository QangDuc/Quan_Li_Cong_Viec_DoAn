@echo off
chcp 65001 > nul
title He Thong Quan Ly Cong Viec Khoa CNTT - HUIT
echo ===================================================
echo  Khoi chay toan bo He thong (Backend + ML + Frontend)
echo ===================================================
call "%~dp0run_backend.bat"
timeout /t 3 /nobreak > nul
start "Frontend UI (Port 5173)" cmd /k "cd /d %~dp0frontend && npm run dev"
echo.
echo ===================================================
echo He thong dang chay!
echo - Web UI:     http://localhost:5173
echo - Swagger UI: http://localhost:8000/docs
echo ===================================================

