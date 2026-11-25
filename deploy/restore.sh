#!/usr/bin/env bash
# ==============================================================================
# InfraScan Linux / Container Automated Restore Script
# Restores PostgreSQL database and file storage from backup archive,
# then executes idempotent migrations to ensure schema consistency.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${SCRIPT_DIR}/../backend/venv/bin/python"

if [ ! -f "${PYTHON_BIN}" ]; then
    PYTHON_BIN="python3"
fi

echo "[*] Starting InfraScan Restore..."
"${PYTHON_BIN}" "${SCRIPT_DIR}/backup_manager.py" restore "$@"

echo "[SUCCESS] Restore finished cleanly."
exit 0
