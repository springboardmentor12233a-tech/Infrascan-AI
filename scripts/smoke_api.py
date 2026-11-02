"""Exercise the live API with two real sample images.

Run while uvicorn is serving backend/ on http://127.0.0.1:8000:

    backend\\venv\\Scripts\\python scripts\\smoke_api.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8000"
SAMPLES = [
    ROOT / "docs" / "eda_outputs" / "samples" / "deepcrack" / "11120.jpg",
    ROOT / "docs" / "eda_outputs" / "samples" / "rdd2022_czech" / "Czech_000261.jpg",
]


def main() -> None:
    missing = [str(path) for path in SAMPLES if not path.is_file()]
    if missing:
        raise SystemExit(f"Sample images missing: {missing}")

    with httpx.Client(base_url=BASE, timeout=180.0, follow_redirects=True) as client:
        health = client.get("/health")
        health.raise_for_status()
        login = client.post(
            "/auth/login",
            data={"username": "inspector@infrascan.com", "password": "Password123!"},
        )
        login.raise_for_status()
        body = login.json()
        token = body["access_token"]
        user_id = body["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        assets = client.get("/assets", headers=headers)
        assets.raise_for_status()
        asset_items = assets.json().get("items") or assets.json()
        asset_id = asset_items[0]["id"]

        inspection = client.post(
            "/inspections/",
            headers=headers,
            json={
                "asset_id": asset_id,
                "inspector_id": user_id,
                "inspection_date": "2026-11-02",
                "notes": "Milestone demonstration inspection",
                "status": "pending",
            },
        )
        inspection.raise_for_status()
        inspection_id = inspection.json()["id"]

        files = [("files", (path.name, path.read_bytes(), "image/jpeg")) for path in SAMPLES]
        uploaded = client.post(f"/inspections/{inspection_id}/images", headers=headers, files=files)
        uploaded.raise_for_status()

        analyses = []
        for image in uploaded.json():
            analyzed = client.post(f"/images/{image['id']}/analyze", headers=headers)
            analyzed.raise_for_status()
            record = analyzed.json()
            overlay = client.get(record["overlay_url"], headers=headers)
            mask_status = None
            if record.get("mask_url"):
                mask = client.get(record["mask_url"], headers=headers)
                mask_status = mask.status_code
            geometry = (record.get("geometry") or {}).get("measurements") or {}
            analyses.append(
                {
                    "file": image["original_filename"],
                    "image_id": image["id"],
                    "quality_status": record["quality"].get("status"),
                    "classification": record.get("classification_label"),
                    "classification_status": record.get("classification_status"),
                    "classification_confidence": record.get("classification_confidence"),
                    "detection_status": record.get("detection_status"),
                    "detection_count": len((record.get("detection") or {}).get("detections") or []),
                    "segmentation_status": record.get("segmentation_status"),
                    "geometry_status": (record.get("geometry") or {}).get("status"),
                    "crack_pixel_area": geometry.get("crack_pixel_area"),
                    "coverage_percent": geometry.get("coverage_percent"),
                    "overlay_status": overlay.status_code,
                    "overlay_bytes": len(overlay.content),
                    "mask_status": mask_status,
                }
            )

        stats = client.get("/stats", headers=headers)
        stats.raise_for_status()
        models = client.get("/models/status", headers=headers)
        models.raise_for_status()
        report = {
            "health": health.json(),
            "asset_id": asset_id,
            "inspection_id": inspection_id,
            "analyses": analyses,
            "stats": stats.json(),
            "models_available": {
                name: block.get("available") for name, block in models.json().items()
            },
        }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"SMOKE_FAILED {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
