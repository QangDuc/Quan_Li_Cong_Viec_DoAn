@echo off
chcp 65001 > nul
set "PATH=C:\Python311;C:\Python311\Scripts;%PATH%"
title Backend & ML Service - HUIT QLCV
echo ===================================================
echo  KHOA LUAN TOT NGHIEP CNTT - HUIT (2026-2027)
echo  Khoi dong Backend API ^& ML Prediction Service
echo ===================================================

echo [1/3] Kiem tra Co so Du lieu...
cd /d %~dp0backend
if not exist qlcv.db (
    echo [Thong bao] Dang khoi tao database va nap du lieu mau...
    python -m app.seed --reset
)

echo [2/3] Khoi dong ML Service (Port 8001)...
start "ML Service (Port 8001)" cmd /k "cd /d %~dp0backend && set PATH=C:\Python311;C:\Python311\Scripts;%%PATH%% && python -m uvicorn ml_service:app --host 127.0.0.1 --port 8001"

timeout /t 3 /nobreak > nul

echo [3/3] Khoi dong Backend API (Port 8000)...
start "Backend API (Port 8000)" cmd /k "cd /d %~dp0backend && set PATH=C:\Python311;C:\Python311\Scripts;%%PATH%% && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo.
echo -> Backend API: http://localhost:8000/docs
echo -> ML Service:  http://localhost:8001/health

