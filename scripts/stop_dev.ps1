# InfraScan Stop Development Environment Script
# Usage: .\scripts\stop_dev.ps1

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Stopping InfraScan Development Services" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Stop processes on port 8000 (Backend)
try {
    $Port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
    if ($Port8000) {
        $pids = $Port8000.OwningProcess | Select-Object -Unique
        foreach ($p in $pids) {
            Write-Host "Stopping Backend process (PID: $p)..." -ForegroundColor Yellow
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
    } else {
        Write-Host "No process listening on port 8000." -ForegroundColor Gray
    }
} catch {
    # Ignore
}

# 2. Stop processes on port 5173 (Frontend)
try {
    $Port5173 = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
    if ($Port5173) {
        $pids = $Port5173.OwningProcess | Select-Object -Unique
        foreach ($p in $pids) {
            Write-Host "Stopping Frontend process (PID: $p)..." -ForegroundColor Yellow
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
    } else {
        Write-Host "No process listening on port 5173." -ForegroundColor Gray
    }
} catch {
    # Ignore
}

# 3. Stop background python worker.py processes
try {
    $WorkerProcesses = Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%worker.py%'" -ErrorAction SilentlyContinue
    if ($WorkerProcesses) {
        foreach ($wp in $WorkerProcesses) {
            Write-Host "Stopping AI Worker process (PID: $($wp.ProcessId))..." -ForegroundColor Yellow
            Stop-Process -Id $wp.ProcessId -Force -ErrorAction SilentlyContinue
        }
    } else {
        Write-Host "No background worker processes found." -ForegroundColor Gray
    }
} catch {
    # Ignore
}

Write-Host "`n[DONE] All InfraScan development services stopped." -ForegroundColor Green
