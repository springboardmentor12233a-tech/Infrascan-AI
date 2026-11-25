"""Phase 4 Database Migration: Jobs Queue, Model Management & Dataset Versions.

Idempotent migration script that prints exact SQL executed.
Safe to run multiple times.
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import inspect, text
from app.database import engine


def run_migration():
    print("=" * 80)
    print("RUNNING PHASE 4 DATABASE MIGRATION (JOBS, MODEL EVENTS, DATASETS)")
    print("=" * 80)

    dialect_name = engine.dialect.name
    print(f"Database Dialect: {dialect_name}")

    with engine.begin() as conn:
        inspector = inspect(conn)
        tables = inspector.get_table_names()

        # 1. Extend 'model_versions' table with real-use metrics
        if "model_versions" in tables:
            cols = [c["name"] for c in inspector.get_columns("model_versions")]
            new_cols = [
                ("inferences_count", "INTEGER NOT NULL DEFAULT 0"),
                ("mean_inference_time_ms", "FLOAT NOT NULL DEFAULT 0.0"),
                ("last_inference_at", "TIMESTAMP WITH TIME ZONE" if dialect_name == "postgresql" else "TIMESTAMP"),
                ("error_count", "INTEGER NOT NULL DEFAULT 0"),
            ]
            for col_name, col_def in new_cols:
                if col_name not in cols:
                    sql = f"ALTER TABLE model_versions ADD COLUMN {col_name} {col_def};"
                    print(f"[SQL] {sql}")
                    conn.execute(text(sql))
                    print(f"  [OK] Added column '{col_name}' to 'model_versions'.")
                else:
                    print(f"  [OK] Column '{col_name}' already exists in 'model_versions'.")

        # 2. Create 'dataset_versions' table
        if "dataset_versions" not in tables:
            print("[SQL] Creating table 'dataset_versions'...")
            if dialect_name == "postgresql":
                sql = """
                CREATE TABLE dataset_versions (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    version VARCHAR(50) NOT NULL,
                    task VARCHAR(50) NOT NULL,
                    split_stats_json TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
                """
            else:
                sql = """
                CREATE TABLE dataset_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL,
                    version VARCHAR(50) NOT NULL,
                    task VARCHAR(50) NOT NULL,
                    split_stats_json TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            print(f"[SQL] {sql.strip()}")
            conn.execute(text(sql))
            print("  [OK] Table 'dataset_versions' created.")
        else:
            print("  [OK] Table 'dataset_versions' already exists.")

        # 3. Create 'model_events' table
        if "model_events" not in tables:
            print("[SQL] Creating table 'model_events'...")
            if dialect_name == "postgresql":
                sql = """
                CREATE TABLE model_events (
                    id SERIAL PRIMARY KEY,
                    model_id VARCHAR(100) NOT NULL REFERENCES model_versions(model_id) ON DELETE CASCADE,
                    event_type VARCHAR(50) NOT NULL,
                    performed_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
                    details_json TEXT,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
                """
            else:
                sql = """
                CREATE TABLE model_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_id VARCHAR(100) NOT NULL REFERENCES model_versions(model_id) ON DELETE CASCADE,
                    event_type VARCHAR(50) NOT NULL,
                    performed_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
                    details_json TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            print(f"[SQL] {sql.strip()}")
            conn.execute(text(sql))
            print("  [OK] Table 'model_events' created.")
        else:
            print("  [OK] Table 'model_events' already exists.")

        # 4. Create 'jobs' table
        if "jobs" not in tables:
            print("[SQL] Creating table 'jobs'...")
            if dialect_name == "postgresql":
                sql = """
                CREATE TABLE jobs (
                    id SERIAL PRIMARY KEY,
                    job_type VARCHAR(50) NOT NULL,
                    payload_json TEXT NOT NULL,
                    status VARCHAR(30) NOT NULL DEFAULT 'pending',
                    progress INTEGER NOT NULL DEFAULT 0,
                    result_json TEXT,
                    error_message TEXT,
                    retries INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 3,
                    user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    started_at TIMESTAMP WITH TIME ZONE,
                    completed_at TIMESTAMP WITH TIME ZONE
                );
                """
            else:
                sql = """
                CREATE TABLE jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_type VARCHAR(50) NOT NULL,
                    payload_json TEXT NOT NULL,
                    status VARCHAR(30) NOT NULL DEFAULT 'pending',
                    progress INTEGER NOT NULL DEFAULT 0,
                    result_json TEXT,
                    error_message TEXT,
                    retries INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 3,
                    user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP
                );
                """
            print(f"[SQL] {sql.strip()}")
            conn.execute(text(sql))
            print("  [OK] Table 'jobs' created.")
        else:
            print("  [OK] Table 'jobs' already exists.")

        # 5. Create indexes
        indexes = [
            ("ix_dataset_versions_name", "dataset_versions", "name"),
            ("ix_model_events_model_id", "model_events", "model_id"),
            ("ix_model_events_created_at", "model_events", "created_at"),
            ("ix_jobs_status", "jobs", "status"),
            ("ix_jobs_job_type", "jobs", "job_type"),
            ("ix_jobs_user_id", "jobs", "user_id"),
            ("ix_jobs_created_at", "jobs", "created_at"),
        ]

        for idx_name, table_name, col_name in indexes:
            sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name}({col_name});"
            print(f"[SQL] {sql}")
            conn.execute(text(sql))

    print("=" * 80)
    print("PHASE 4 MIGRATION COMPLETED SUCCESSFULLY.")
    print("=" * 80)


if __name__ == "__main__":
    run_migration()
