# Start the API and the React app in two windows.
# Run this from any directory after scripts/setup_ml_env.ps1 and npm install.
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root "backend\venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "backend\venv is missing. Run scripts\setup_ml_env.ps1 first."
}

$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
Push-Location $Backend
& $Python seed_data.py
Pop-Location

Start-Process powershell -WorkingDirectory $Backend -ArgumentList "-NoExit", "-Command", "& `"$Python`" -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
Start-Process powershell -WorkingDirectory $Frontend -ArgumentList "-NoExit", "-Command", "npm run dev"
Write-Output "Backend: http://127.0.0.1:8000/docs"
Write-Output "Frontend: http://127.0.0.1:5173"
Write-Output "Login: inspector@infrascan.com / Password123!"
