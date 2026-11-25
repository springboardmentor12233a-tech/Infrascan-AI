#!/usr/bin/env bash
# ==============================================================================
# InfraScan Linux / Container Automated Backup Script
# Dumps PostgreSQL database, compresses storage uploads, verifies integrity,
# and enforces retention policy (7 daily + 4 weekly backups).
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${SCRIPT_DIR}/../backend/venv/bin/python"

if [ ! -f "${PYTHON_BIN}" ]; then
    PYTHON_BIN="python3"
fi

echo "[*] Starting InfraScan Backup..."
"${PYTHON_BIN}" "${SCRIPT_DIR}/backup_manager.py" backup "$@"

echo "[SUCCESS] Backup finished cleanly."
exit 0
