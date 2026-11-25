"""Unified database migration script for Milestone 3 Part 2 (Phases A, B, C, D).

Applies:
1. Phase A:
   - Adds nullable column 'district' (VARCHAR(100)) to 'infrastructure_assets'.
2. Phase B:
   - Creates 'inspection_comparisons' table.
   - Creates 'image_comparisons' table.
3. Phase C:
   - Adds nullable column 'risk_factors_json' (TEXT) to 'infrastructure_assets'.
   - Adds nullable column 'next_inspection_due' (DATE) to 'infrastructure_assets'.
   - Creates 'maintenance_priorities' table.
   - Creates 'maintenance_tasks' table.
   - Creates 'maintenance_task_events' table.
4. Phase D:
   - Creates 'demo_markers' table.
   - Creates performance indexes on images, analysis_runs, severity_assessments,
     detections, inspections, and maintenance_tasks.

Safe to execute multiple times (idempotent). Prints exact SQL executed.
"""

import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import inspect, text
from app.database import engine, Base


def run_migration():
    print("=" * 80)
    print("RUNNING MILESTONE 3 PART 2 DATABASE MIGRATION (PHASES A, B, C, D)")
    print("=" * 80)

    dialect_name = engine.dialect.name
    print(f"Database Dialect: {dialect_name}")

    with engine.begin() as conn:
        inspector = inspect(conn)
        existing_tables = set(inspector.get_table_names())

        # ----------------------------------------------------------------------
        # 1. Phase A: Add 'district' to 'infrastructure_assets'
        # ----------------------------------------------------------------------
        if "infrastructure_assets" in existing_tables:
            asset_cols = {c["name"] for c in inspector.get_columns("infrastructure_assets")}
            if "district" not in asset_cols:
                sql = "ALTER TABLE infrastructure_assets ADD COLUMN district VARCHAR(100);"
                print(f"[SQL] {sql}")
                conn.execute(text(sql))
                print("  -> Added column 'district' to 'infrastructure_assets'.")
            else:
                print("  [OK] Column 'district' already exists on 'infrastructure_assets'.")

            # Phase C asset columns: 'risk_factors_json' and 'next_inspection_due'
            if "risk_factors_json" not in asset_cols:
                sql = "ALTER TABLE infrastructure_assets ADD COLUMN risk_factors_json TEXT;"
                print(f"[SQL] {sql}")
                conn.execute(text(sql))
                print("  -> Added column 'risk_factors_json' to 'infrastructure_assets'.")
            else:
                print("  [OK] Column 'risk_factors_json' already exists on 'infrastructure_assets'.")

            if "next_inspection_due" not in asset_cols:
                sql = "ALTER TABLE infrastructure_assets ADD COLUMN next_inspection_due DATE;"
                print(f"[SQL] {sql}")
                conn.execute(text(sql))
                print("  -> Added column 'next_inspection_due' to 'infrastructure_assets'.")
            else:
                print("  [OK] Column 'next_inspection_due' already exists on 'infrastructure_assets'.")

        # ----------------------------------------------------------------------
        # 2. Phase B: Inspection & Image Comparison Tables
        # ----------------------------------------------------------------------
        if "inspection_comparisons" not in existing_tables:
            if dialect_name == "postgresql":
                sql = """
                CREATE TABLE inspection_comparisons (
                    comparison_id SERIAL PRIMARY KEY,
                    asset_id INTEGER NOT NULL REFERENCES infrastructure_assets(asset_id) ON DELETE CASCADE,
                    prev_inspection_id INTEGER NOT NULL REFERENCES inspections(inspection_id) ON DELETE CASCADE,
                    curr_inspection_id INTEGER NOT NULL REFERENCES inspections(inspection_id) ON DELETE CASCADE,
                    created_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
                    summary_json TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
                """
            else:
                sql = """
                CREATE TABLE inspection_comparisons (
                    comparison_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_id INTEGER NOT NULL REFERENCES infrastructure_assets(asset_id) ON DELETE CASCADE,
                    prev_inspection_id INTEGER NOT NULL REFERENCES inspections(inspection_id) ON DELETE CASCADE,
                    curr_inspection_id INTEGER NOT NULL REFERENCES inspections(inspection_id) ON DELETE CASCADE,
                    created_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
                    summary_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
                """
            print(f"[SQL] {sql.strip()}")
            conn.execute(text(sql))
            print("  -> Created table 'inspection_comparisons'.")
        else:
            print("  [OK] Table 'inspection_comparisons' already exists.")

        if "image_comparisons" not in existing_tables:
            if dialect_name == "postgresql":
                sql = """
                CREATE TABLE image_comparisons (
                    id SERIAL PRIMARY KEY,
                    comparison_id INTEGER NOT NULL REFERENCES inspection_comparisons(comparison_id) ON DELETE CASCADE,
                    prev_image_id INTEGER NOT NULL REFERENCES images(image_id) ON DELETE CASCADE,
                    curr_image_id INTEGER NOT NULL REFERENCES images(image_id) ON DELETE CASCADE,
                    status VARCHAR(30) NOT NULL,
                    inliers INTEGER,
                    inlier_ratio DOUBLE PRECISION,
                    reprojection_rmse DOUBLE PRECISION,
                    overlap_share DOUBLE PRECISION,
                    homography_json TEXT,
                    metrics_json TEXT,
                    warnings_json TEXT,
                    overlay_path VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
                """
            else:
                sql = """
                CREATE TABLE image_comparisons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    comparison_id INTEGER NOT NULL REFERENCES inspection_comparisons(comparison_id) ON DELETE CASCADE,
                    prev_image_id INTEGER NOT NULL REFERENCES images(image_id) ON DELETE CASCADE,
                    curr_image_id INTEGER NOT NULL REFERENCES images(image_id) ON DELETE CASCADE,
                    status VARCHAR(30) NOT NULL,
                    inliers INTEGER,
                    inlier_ratio FLOAT,
                    reprojection_rmse FLOAT,
                    overlap_share FLOAT,
                    homography_json TEXT,
                    metrics_json TEXT,
                    warnings_json TEXT,
                    overlay_path VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
                """
            print(f"[SQL] {sql.strip()}")
            conn.execute(text(sql))
            print("  -> Created table 'image_comparisons'.")
        else:
            print("  [OK] Table 'image_comparisons' already exists.")

        # ----------------------------------------------------------------------
        # 3. Phase C: Maintenance Priorities, Tasks, Events
        # ----------------------------------------------------------------------
        if "maintenance_priorities" not in existing_tables:
            if dialect_name == "postgresql":
                sql = """
                CREATE TABLE maintenance_priorities (
                    priority_id SERIAL PRIMARY KEY,
                    asset_id INTEGER NOT NULL REFERENCES infrastructure_assets(asset_id) ON DELETE CASCADE,
                    inspection_id INTEGER REFERENCES inspections(inspection_id) ON DELETE CASCADE,
                    suggested_priority VARCHAR(50) NOT NULL,
                    final_priority VARCHAR(50),
                    provisional BOOLEAN NOT NULL DEFAULT TRUE,
                    factors_json TEXT,
                    flags_json TEXT,
                    rules_version VARCHAR(50),
                    rules_sha256 VARCHAR(64),
                    status VARCHAR(50) NOT NULL DEFAULT 'suggested',
                    reviewed_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
                    reviewed_at TIMESTAMP WITH TIME ZONE,
                    review_comment TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
                """
            else:
                sql = """
                CREATE TABLE maintenance_priorities (
                    priority_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_id INTEGER NOT NULL REFERENCES infrastructure_assets(asset_id) ON DELETE CASCADE,
                    inspection_id INTEGER REFERENCES inspections(inspection_id) ON DELETE CASCADE,
                    suggested_priority VARCHAR(50) NOT NULL,
                    final_priority VARCHAR(50),
                    provisional BOOLEAN NOT NULL DEFAULT 1,
                    factors_json TEXT,
                    flags_json TEXT,
                    rules_version VARCHAR(50),
                    rules_sha256 VARCHAR(64),
                    status VARCHAR(50) NOT NULL DEFAULT 'suggested',
                    reviewed_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
                    reviewed_at TIMESTAMP,
                    review_comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
                """
            print(f"[SQL] {sql.strip()}")
            conn.execute(text(sql))
            print("  -> Created table 'maintenance_priorities'.")
        else:
            print("  [OK] Table 'maintenance_priorities' already exists.")

        if "maintenance_tasks" not in existing_tables:
            if dialect_name == "postgresql":
                sql = """
                CREATE TABLE maintenance_tasks (
                    task_id SERIAL PRIMARY KEY,
                    asset_id INTEGER NOT NULL REFERENCES infrastructure_assets(asset_id) ON DELETE CASCADE,
                    inspection_id INTEGER REFERENCES inspections(inspection_id) ON DELETE SET NULL,
                    priority_id INTEGER REFERENCES maintenance_priorities(priority_id) ON DELETE SET NULL,
                    title VARCHAR(200) NOT NULL,
                    description TEXT,
                    task_type VARCHAR(50) NOT NULL,
                    priority VARCHAR(50) NOT NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'open',
                    assigned_to INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
                    created_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
                    due_date DATE,
                    started_at TIMESTAMP WITH TIME ZONE,
                    completed_at TIMESTAMP WITH TIME ZONE,
                    resolution_notes TEXT,
                    follow_up_inspection_id INTEGER REFERENCES inspections(inspection_id) ON DELETE SET NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
                """
            else:
                sql = """
                CREATE TABLE maintenance_tasks (
                    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_id INTEGER NOT NULL REFERENCES infrastructure_assets(asset_id) ON DELETE CASCADE,
                    inspection_id INTEGER REFERENCES inspections(inspection_id) ON DELETE SET NULL,
                    priority_id INTEGER REFERENCES maintenance_priorities(priority_id) ON DELETE SET NULL,
                    title VARCHAR(200) NOT NULL,
                    description TEXT,
                    task_type VARCHAR(50) NOT NULL,
                    priority VARCHAR(50) NOT NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'open',
                    assigned_to INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
                    created_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
                    due_date DATE,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    resolution_notes TEXT,
                    follow_up_inspection_id INTEGER REFERENCES inspections(inspection_id) ON DELETE SET NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
                """
            print(f"[SQL] {sql.strip()}")
            conn.execute(text(sql))
            print("  -> Created table 'maintenance_tasks'.")
        else:
            print("  [OK] Table 'maintenance_tasks' already exists.")

        if "maintenance_task_events" not in existing_tables:
            if dialect_name == "postgresql":
                sql = """
                CREATE TABLE maintenance_task_events (
                    event_id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL REFERENCES maintenance_tasks(task_id) ON DELETE CASCADE,
                    user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
                    event_type VARCHAR(50) NOT NULL,
                    old_value VARCHAR(100),
                    new_value VARCHAR(100),
                    comment TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
                """
            else:
                sql = """
                CREATE TABLE maintenance_task_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL REFERENCES maintenance_tasks(task_id) ON DELETE CASCADE,
                    user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
                    event_type VARCHAR(50) NOT NULL,
                    old_value VARCHAR(100),
                    new_value VARCHAR(100),
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
                """
            print(f"[SQL] {sql.strip()}")
            conn.execute(text(sql))
            print("  -> Created table 'maintenance_task_events'.")
        else:
            print("  [OK] Table 'maintenance_task_events' already exists.")

        # ----------------------------------------------------------------------
        # 4. Phase D: Demo Markers and Performance Indexes
        # ----------------------------------------------------------------------
        if "demo_markers" not in existing_tables:
            if dialect_name == "postgresql":
                sql = """
                CREATE TABLE demo_markers (
                    marker_id SERIAL PRIMARY KEY,
                    entity_type VARCHAR(50) NOT NULL,
                    entity_id VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
                """
            else:
                sql = """
                CREATE TABLE demo_markers (
                    marker_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type VARCHAR(50) NOT NULL,
                    entity_id VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
                """
            print(f"[SQL] {sql.strip()}")
            conn.execute(text(sql))
            print("  -> Created table 'demo_markers'.")
        else:
            print("  [OK] Table 'demo_markers' already exists.")

        # Indexes for Phase D
        indexes_to_create = [
            ("ix_images_inspection_id", "CREATE INDEX IF NOT EXISTS ix_images_inspection_id ON images(inspection_id);"),
            ("ix_analysis_runs_image_id", "CREATE INDEX IF NOT EXISTS ix_analysis_runs_image_id ON analysis_runs(image_id);"),
            ("ix_severity_assessments_image_run", "CREATE INDEX IF NOT EXISTS ix_severity_assessments_image_run ON severity_assessments(image_id, run_id);"),
            ("ix_detections_run_id", "CREATE INDEX IF NOT EXISTS ix_detections_run_id ON detections(run_id);"),
            ("ix_inspections_asset_date", "CREATE INDEX IF NOT EXISTS ix_inspections_asset_date ON inspections(asset_id, inspection_date);"),
            ("ix_maintenance_tasks_status_assigned_due", "CREATE INDEX IF NOT EXISTS ix_maintenance_tasks_status_assigned_due ON maintenance_tasks(status, assigned_to, due_date);"),
            ("ix_demo_markers_type_id", "CREATE INDEX IF NOT EXISTS ix_demo_markers_type_id ON demo_markers(entity_type, entity_id);"),
        ]

        for idx_name, idx_sql in indexes_to_create:
            try:
                print(f"[SQL] {idx_sql}")
                conn.execute(text(idx_sql))
            except Exception as e:
                print(f"  Note on index {idx_name}: {e}")

    print("=" * 80)
    print("MIGRATION COMPLETED SUCCESSFULLY.")
    print("=" * 80)


if __name__ == "__main__":
    run_migration()
