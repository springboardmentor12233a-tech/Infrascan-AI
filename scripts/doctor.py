import os
import sys
from pathlib import Path

# Forward to backend/scripts/doctor.py
backend_script = Path(__file__).resolve().parent.parent / "backend" / "scripts" / "doctor.py"
if backend_script.exists():
    import importlib.util
    spec = importlib.util.spec_from_file_location("doctor_main", str(backend_script))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["doctor_main"] = mod
    spec.loader.exec_module(mod)
    if hasattr(mod, "run_doctor"):
        import argparse
        parser = argparse.ArgumentParser(description="InfraScan Doctor Diagnostic Tool")
        parser.add_argument("--fix", action="store_true", help="Perform safe automated fixes")
        args, _ = parser.parse_known_args()
        mod.run_doctor(fix=args.fix)
