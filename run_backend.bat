@echo off
chcp 65001 > nul
title Backend and ML Service - HUIT QLCV
echo ===================================================
echo  KHOA LUAN TOT NGHIEP CNTT - HUIT (2026-2027)
echo  Khoi dong Backend API va ML Prediction Service
echo ===================================================

cd /d "%~dp0"

if exist "%~dp0.venv\Scripts\activate.bat" (
    call "%~dp0.venv\Scripts\activate.bat"
)

echo [1/3] Kiem tra Co so Du lieu...
cd /d "%~dp0backend"
python -m app.seed

echo [2/3] Khoi dong ML Service (Port 8001)...
start "ML Service (Port 8001)" /D "%~dp0backend" cmd /k "call ..\.venv\Scripts\activate.bat && python -m uvicorn ml_service:app --host 127.0.0.1 --port 8001"

ping 127.0.0.1 -n 4 > nul

echo [3/3] Khoi dong Backend API (Port 8000)...
start "Backend API (Port 8000)" /D "%~dp0backend" cmd /k "call ..\.venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo.
echo - Backend API: http://localhost:8000/docs
echo - ML Service:  http://localhost:8001/health
