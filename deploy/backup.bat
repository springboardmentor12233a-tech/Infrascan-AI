@echo off
REM ============================================================================
REM InfraScan Windows Automated Backup Script
REM Dumps PostgreSQL database, compresses storage uploads, verifies integrity,
REM and enforces retention policy (7 daily + 4 weekly backups).
REM ============================================================================

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set PYTHON_BIN=%SCRIPT_DIR%..\backend\venv\Scripts\python.exe

if not exist "%PYTHON_BIN%" (
    set PYTHON_BIN=python
)

echo [*] Starting InfraScan Backup...
"%PYTHON_BIN%" "%SCRIPT_DIR%backup_manager.py" backup %*

if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Backup finished cleanly.
    exit /b 0
) else (
    echo [ERROR] Backup failed with exit code %ERRORLEVEL%.
    exit /b %ERRORLEVEL%
)
