"""Export OpenAPI schema to docs/final/openapi.json."""

import json
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.main import app

output_path = backend_dir.parent.parent / "docs" / "final" / "openapi.json"
if not output_path.parent.exists():
    output_path = backend_dir.parent / "docs" / "final" / "openapi.json"

output_path.parent.mkdir(parents=True, exist_ok=True)
schema = app.openapi()

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(schema, f, indent=2)

print(f"Exported OpenAPI schema with {len(schema.get('paths', {}))} endpoints to {output_path}")
