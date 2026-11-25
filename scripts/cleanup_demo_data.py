import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
SCRIPT_PATH = BACKEND_DIR / "scripts" / "cleanup_demo_data.py"

if __name__ == "__main__":
    venv_python = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
    exe = str(venv_python) if venv_python.exists() else sys.executable
    sys.exit(subprocess.call([exe, str(SCRIPT_PATH)] + sys.argv[1:]))
