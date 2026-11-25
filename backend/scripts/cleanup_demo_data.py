"""Cleanup Demo Data from InfraScan Database.

Removes all rows marked in `demo_markers`.
Supports `--dry-run` flag to preview deletions safely.
"""

import argparse
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.models.asset import InfrastructureAsset
from app.models.demo import DemoMarker
from app.models.inspection import Inspection
from app.models.severity import InspectionSeverity


def cleanup_demo_data(dry_run: bool = False) -> None:
    db = SessionLocal()
    try:
        markers = db.query(DemoMarker).all()
        print(f"[INFO] Found {len(markers)} demo markers in database.")

        asset_ids = [int(m.entity_id) for m in markers if m.entity_type == "asset" and m.entity_id.isdigit()]
        insp_ids = [int(m.entity_id) for m in markers if m.entity_type == "inspection" and m.entity_id.isdigit()]
        sev_ids = [int(m.entity_id) for m in markers if m.entity_type == "inspection_severity" and m.entity_id.isdigit()]

        print(f"  - Demo Assets to remove: {len(asset_ids)}")
        print(f"  - Demo Inspections to remove: {len(insp_ids)}")
        print(f"  - Demo Severities to remove: {len(sev_ids)}")

        if dry_run:
            print("[DRY-RUN] No rows were modified or deleted.")
            return

        # Perform actual deletions in reverse dependency order
        if sev_ids:
            db.query(InspectionSeverity).filter(InspectionSeverity.id.in_(sev_ids)).delete(synchronize_session=False)

        if insp_ids:
            db.query(Inspection).filter(Inspection.inspection_id.in_(insp_ids)).delete(synchronize_session=False)

        if asset_ids:
            db.query(InfrastructureAsset).filter(InfrastructureAsset.asset_id.in_(asset_ids)).delete(synchronize_session=False)

        # Delete markers
        deleted_markers = db.query(DemoMarker).delete(synchronize_session=False)
        db.commit()

        print(f"[SUCCESS] Cleaned up {deleted_markers} demo markers and their linked records.")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to clean up demo data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cleanup demo data.")
    parser.add_argument("--dry-run", action="store_true", help="Preview deletions without modifying database")
    args = parser.parse_args()
    cleanup_demo_data(dry_run=args.dry_run)
