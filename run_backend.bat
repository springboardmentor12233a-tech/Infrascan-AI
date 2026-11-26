@echo off
echo Starting InfraScan FastAPI Backend on http://localhost:8000...
cd /d "E:\infosys\Internship\InfraScan\backend"
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
