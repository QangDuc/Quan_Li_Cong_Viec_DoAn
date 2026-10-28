@echo off
chcp 65001 > nul
title Backend & ML Service - HUIT QLCV
echo ===================================================
echo  KHOA LUAN TOT NGHIEP CNTT - HUIT (2026-2027)
echo  Khoi dong Backend API ^& ML Prediction Service
echo ===================================================

echo [1/3] Kiem tra SQL Server LocalDB...
sqllocaldb start MSSQLLocalDB > nul 2>&1

echo [2/3] Khoi dong ML Service (Port 8001)...
start "ML Service (Port 8001)" cmd /k "cd /d %~dp0backend && python -m uvicorn ml_service:app --host 127.0.0.1 --port 8001"

timeout /t 6 /nobreak > nul

echo [3/3] Khoi dong Backend API (Port 8000)...
start "Backend API (Port 8000)" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo.
echo -> Backend API: http://localhost:8000/docs
echo -> ML Service:  http://localhost:8001/health

