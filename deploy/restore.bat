@echo off
REM ============================================================================
REM InfraScan Windows Automated Restore Script
REM Restores PostgreSQL database and file storage from backup archive,
REM then executes idempotent migrations to ensure schema consistency.
REM ============================================================================

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set PYTHON_BIN=%SCRIPT_DIR%..\backend\venv\Scripts\python.exe

if not exist "%PYTHON_BIN%" (
    set PYTHON_BIN=python
)

echo [*] Starting InfraScan Restore...
"%PYTHON_BIN%" "%SCRIPT_DIR%backup_manager.py" restore %*

if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Restore completed successfully.
    exit /b 0
) else (
    echo [ERROR] Restore failed with exit code %ERRORLEVEL%.
    exit /b %ERRORLEVEL%
)
