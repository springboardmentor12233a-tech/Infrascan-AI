"""
smoke_test.py – quick Phase 1 verification.
Run with: python smoke_test.py   (from backend/ with venv active)

This is NOT part of the production code – it's a helper for the developer.
"""

import sys
import urllib.request
import urllib.error
import json

BASE = "http://localhost:8000"


def check(label: str, url: str, expected_key: str, expected_value: str) -> bool:
    print(f"\n  Testing {label}...", end=" ")
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            data = json.loads(r.read())
            if data.get(expected_key) == expected_value:
                print(f"✅  {data}")
                return True
            else:
                print(f"❌  Unexpected response: {data}")
                return False
    except urllib.error.URLError as e:
        print(f"❌  Could not connect: {e}")
        return False


if __name__ == "__main__":
    print("\n🔍 InfraScan Phase 1 Smoke Test")
    print("=" * 40)

    passed = check("/health", f"{BASE}/health", "status", "ok")

    print("\n" + "=" * 40)
    if passed:
        print("✅  All checks passed! Phase 1 is working.\n")
    else:
        print("❌  Some checks failed. Is the server running?")
        print("    Run: uvicorn app.main:app --reload\n")
        sys.exit(1)
