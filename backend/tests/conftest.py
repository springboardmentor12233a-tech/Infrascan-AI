import sys
from pathlib import Path

# Automatically ensure 'backend' and root are on sys.path for backend test suite
backend_dir = Path(__file__).resolve().parents[1]
root_dir = Path(__file__).resolve().parents[2]

for p in (str(backend_dir), str(root_dir)):
    if p not in sys.path:
        sys.path.insert(0, p)
