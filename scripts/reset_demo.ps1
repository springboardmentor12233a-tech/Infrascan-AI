# InfraScan Reset Demo Data Script (Development Only)
# Usage: .\scripts\reset_demo.ps1

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " InfraScan Reset Demo Data & Seed Credentials" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$InfrascanRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $InfrascanRoot "backend"
$PythonExe = Join-Path $BackendDir "venv\Scripts\python.exe"

# 1. Cleanup Old Demo Data
Write-Host "`n[STEP 1/3] Cleaning up old demo markers & linked data..." -ForegroundColor Yellow
$CleanupScript = Join-Path $BackendDir "scripts\cleanup_demo_data.py"
& $PythonExe $CleanupScript

# 2. Seed Fresh Demo Users (Writes to docs/final/demo_accounts.local.txt)
Write-Host "`n[STEP 2/3] Seeding demo user accounts for all 5 roles..." -ForegroundColor Yellow
$SeedUsersScript = Join-Path $BackendDir "scripts\seed_demo_users.py"
& $PythonExe $SeedUsersScript

# 3. Seed Fresh Demo Map Assets & Inspections
Write-Host "`n[STEP 3/3] Seeding 10+ demo assets and inspections around Chennai..." -ForegroundColor Yellow
$SeedDataScript = Join-Path $BackendDir "scripts\seed_demo_data.py"
& $PythonExe $SeedDataScript

Write-Host "`n[SUCCESS] Demo environment successfully reset!" -ForegroundColor Green
Write-Host "Demo credentials saved to: docs\final\demo_accounts.local.txt (gitignored)" -ForegroundColor White
