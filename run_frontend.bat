@echo off
chcp 65001 > nul
set "PATH=C:\nodejs;%PATH%"
title Frontend UI - HUIT QLCV
echo ===================================================
echo  Khoi dong Giao dien Web React Vite (Port 5173)
echo ===================================================
cd /d "%~dp0frontend"
if not exist node_modules (
    echo [Thong bao] Dang cai dat dependencies lan dau (npm install)...
    npm install
)
npm run dev
