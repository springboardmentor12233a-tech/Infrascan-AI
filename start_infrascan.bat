@echo off
echo ========================================================
echo   InfraScan — AI Infrastructure Damage Assessment System
echo ========================================================
echo.
echo Launching Backend (FastAPI on Port 8000)...
start "InfraScan Backend" cmd /k "cd /d E:\infosys\Internship\InfraScan\backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000"

echo Waiting for backend to initialize...
timeout /t 3 /nobreak >nul

echo Launching Frontend (Vite React on Port 5173)...
start "InfraScan Frontend" cmd /k "cd /d E:\infosys\Internship\InfraScan\frontend && npm run dev"

echo.
echo ========================================================
echo InfraScan is running!
echo Access the Web Application at: http://localhost:5173
echo Backend API Docs at:           http://localhost:8000/docs
echo ========================================================
pause
