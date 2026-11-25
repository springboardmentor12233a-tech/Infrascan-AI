# InfraScan One-Command Development Orchestration Script
# Usage: .\scripts\run_dev.ps1

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " InfraScan Real-Time Development Environment Startup" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$InfrascanRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $InfrascanRoot "backend"
$FrontendDir = Join-Path $InfrascanRoot "frontend"
$PythonExe = Join-Path $BackendDir "venv\Scripts\python.exe"

# 1. Check Python
if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Python venv not found at: $PythonExe" -ForegroundColor Red
    exit 1
}
$PyVer = & $PythonExe --version
Write-Host "[OK] Python: $PyVer" -ForegroundColor Green

# 2. Check Node
try {
    $NodeVer = node --version
    Write-Host "[OK] Node.js: $NodeVer" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Node.js is not found in PATH." -ForegroundColor Red
    exit 1
}

# 3. Run Pre-flight System Doctor
Write-Host "`n[STEP 1/5] Running System Pre-flight Diagnostics..." -ForegroundColor Yellow
$DoctorScript = Join-Path $BackendDir "scripts\doctor.py"
& $PythonExe $DoctorScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Doctor checks failed. Please fix reported errors before running." -ForegroundColor Red
    exit 1
}

# 4. Initialize Database & Migrations
Write-Host "`n[STEP 2/5] Applying Database Migrations & Initializing DB..." -ForegroundColor Yellow
$InitDbScript = Join-Path $BackendDir "scripts\init_db.py"
& $PythonExe $InitDbScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Database initialization failed." -ForegroundColor Red
    exit 1
}

# 5. Start Backend Process in New Window
Write-Host "`n[STEP 3/5] Starting FastAPI Backend on 127.0.0.1:8000..." -ForegroundColor Yellow
$BackendCmd = "cd '$BackendDir'; .\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$BackendCmd" -WindowStyle Normal

# 6. Start AI Background Worker in New Window
Write-Host "`n[STEP 4/5] Starting AI Job Worker (SKIP LOCKED & Heartbeat)..." -ForegroundColor Yellow
$WorkerCmd = "cd '$BackendDir'; .\venv\Scripts\python.exe app\worker.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$WorkerCmd" -WindowStyle Normal

# 7. Start Frontend Dev Server in New Window
Write-Host "`n[STEP 5/5] Starting Vite Frontend on 127.0.0.1:5173..." -ForegroundColor Yellow
$FrontendCmd = "cd '$FrontendDir'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$FrontendCmd" -WindowStyle Normal

# 8. Poll /readyz until Backend is Healthy
Write-Host "`nWaiting for backend /readyz probe..." -ForegroundColor Cyan
$Ready = $false
$Attempts = 0
$MaxAttempts = 30
while (-not $Ready -and $Attempts -lt $MaxAttempts) {
    Start-Sleep -Seconds 1
    $Attempts++
    try {
        $Response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/readyz" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($Response.status -eq "ready") {
            $Ready = $true
        }
    } catch {
        # Retry
    }
    Write-Host "." -NoNewline
}

if ($Ready) {
    Write-Host "`n`n==========================================================" -ForegroundColor Green
    Write-Host " [SUCCESS] InfraScan is running and fully initialized!" -ForegroundColor Green
    Write-Host " - Frontend: http://127.0.0.1:5173" -ForegroundColor White
    Write-Host " - Backend API: http://127.0.0.1:8000" -ForegroundColor White
    Write-Host " - OpenAPI Docs: http://127.0.0.1:8000/docs" -ForegroundColor White
    Write-Host " To stop all services, run: .\scripts\stop_dev.ps1" -ForegroundColor Yellow
    Write-Host "==========================================================" -ForegroundColor Green

    # Open Browser
    Start-Process "http://127.0.0.1:5173"
} else {
    Write-Host "`n`n[WARNING] Backend timed out while waiting for /readyz." -ForegroundColor Yellow
    Write-Host "Please check the opened backend and worker terminal windows for error logs." -ForegroundColor Yellow
}
