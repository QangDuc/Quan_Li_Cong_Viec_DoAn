@echo off
chcp 65001 > nul
title Frontend UI - HUIT QLCV
echo ===================================================
echo  Khoi dong Giao dien Web React Vite (Port 5173)
echo ===================================================
cd /d %~dp0frontend
npm run dev

