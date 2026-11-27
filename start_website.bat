@echo off
title InfraScan Launcher
echo ========================================================
echo       Starting InfraScan AI Infrastructure System        
echo ========================================================
echo.
echo [1/2] Starting Backend API (FastAPI + Uvicorn)...
start "InfraScan - Backend (FastAPI)" cmd /k "cd /d "%~dp0backend" && ..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

echo [2/2] Starting Frontend (React + Vite)...
start "InfraScan - Frontend (React)" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo ========================================================
echo Both servers have been launched in separate windows!
echo - Web Application:   http://localhost:5173
echo - API Documentation: http://127.0.0.1:8000/docs
echo ========================================================
echo.
echo Press any key to close this launcher window (servers will stay running)...
pause >nul
