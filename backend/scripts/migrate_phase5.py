"""Phase 5 Database Optimization Migration: Indexes for High-Performance Queries.

Adds composite and specialized performance indexes to support:
- Map geospatial queries (latitude, longitude)
- Filtered image listings and inspections
- Detections and severity assessments
- Background job worker polling (status, created_at)
- Notification unread queries
"""

import sys
from pathlib import Path
from sqlalchemy import text

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.database import engine

INDEXES_SQL = [
    (
        "ix_assets_lat_lng",
        "CREATE INDEX IF NOT EXISTS ix_assets_lat_lng ON infrastructure_assets (latitude, longitude);",
    ),
    (
        "ix_inspections_asset_date",
        "CREATE INDEX IF NOT EXISTS ix_inspections_asset_date ON inspections (asset_id, inspection_date);",
    ),
    (
        "ix_images_inspection_quality",
        "CREATE INDEX IF NOT EXISTS ix_images_inspection_quality ON images (inspection_id, quality_status);",
    ),
    (
        "ix_detections_run_conf",
        "CREATE INDEX IF NOT EXISTS ix_detections_run_conf ON detections (run_id, confidence);",
    ),
    (
        "ix_detections_damage_type",
        "CREATE INDEX IF NOT EXISTS ix_detections_damage_type ON detections (damage_type);",
    ),
    (
        "ix_jobs_status_created",
        "CREATE INDEX IF NOT EXISTS ix_jobs_status_created ON jobs (status, created_at);",
    ),
    (
        "ix_notifications_user_read",
        "CREATE INDEX IF NOT EXISTS ix_notifications_user_read ON notifications (user_id, read_at, created_at);",
    ),
]


def run_migration():
    print("=" * 70)
    print("Starting Phase 5 Database Optimization Migration (Performance Indexes)")
    print("=" * 70)

    with engine.connect() as conn:
        for idx_name, sql in INDEXES_SQL:
            print(f"[SQL] {sql}")
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"[OK] Index '{idx_name}' created or already exists.")
            except Exception as e:
                print(f"[WARN] Failed to create index '{idx_name}': {e}")

    print("\nPhase 5 Database Optimization Migration Completed Successfully.")


if __name__ == "__main__":
    run_migration()
