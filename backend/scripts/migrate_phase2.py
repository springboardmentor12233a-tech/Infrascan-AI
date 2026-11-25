"""Idempotent Migration Script for Phase 2: Reports and Multi-format Exports.
Prints all executed SQL statements. Safe to run repeatedly.
"""
import sys
from pathlib import Path
from sqlalchemy import text, inspect

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database import engine


def run_migration():
    print("=" * 80)
    print("RUNNING PHASE 2 DATABASE MIGRATION (REPORTS AND REPORT FILES)")
    print("=" * 80)

    dialect = engine.dialect.name
    print(f"Database Dialect: {dialect}")

    with engine.begin() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())

        # 1. reports table
        if "reports" not in tables:
            print("[SQL] Creating table 'reports'...")
            if dialect == "postgresql":
                sql = """
                CREATE TABLE reports (
                    report_id SERIAL PRIMARY KEY,
                    inspection_id INTEGER NOT NULL REFERENCES inspections(inspection_id) ON DELETE CASCADE,
                    version INTEGER NOT NULL DEFAULT 1,
                    status VARCHAR(50) NOT NULL DEFAULT 'draft',
                    generated_by INTEGER NOT NULL REFERENCES users(user_id),
                    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    content_sha256 VARCHAR(64) NOT NULL,
                    snapshot_json_path VARCHAR(500) NOT NULL,
                    model_versions_json TEXT NULL,
                    rules_versions_json TEXT NULL,
                    review_summary_json TEXT NULL,
                    notes TEXT NULL
                );
                """
            else:
                sql = """
                CREATE TABLE reports (
                    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inspection_id INTEGER NOT NULL REFERENCES inspections(inspection_id) ON DELETE CASCADE,
                    version INTEGER NOT NULL DEFAULT 1,
                    status VARCHAR(50) NOT NULL DEFAULT 'draft',
                    generated_by INTEGER NOT NULL REFERENCES users(user_id),
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    content_sha256 VARCHAR(64) NOT NULL,
                    snapshot_json_path VARCHAR(500) NOT NULL,
                    model_versions_json TEXT NULL,
                    rules_versions_json TEXT NULL,
                    review_summary_json TEXT NULL,
                    notes TEXT NULL
                );
                """
            print(sql.strip())
            conn.execute(text(sql))
        else:
            print("  [OK] Table 'reports' already exists.")

        # 2. report_files table
        if "report_files" not in tables:
            print("[SQL] Creating table 'report_files'...")
            if dialect == "postgresql":
                sql = """
                CREATE TABLE report_files (
                    file_id SERIAL PRIMARY KEY,
                    report_id INTEGER NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,
                    format VARCHAR(20) NOT NULL,
                    path VARCHAR(500) NOT NULL,
                    size INTEGER NOT NULL,
                    sha256 VARCHAR(64) NOT NULL
                );
                """
            else:
                sql = """
                CREATE TABLE report_files (
                    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id INTEGER NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,
                    format VARCHAR(20) NOT NULL,
                    path VARCHAR(500) NOT NULL,
                    size INTEGER NOT NULL,
                    sha256 VARCHAR(64) NOT NULL
                );
                """
            print(sql.strip())
            conn.execute(text(sql))
        else:
            print("  [OK] Table 'report_files' already exists.")

        # 3. Indexes
        indexes = [
            ("ix_reports_inspection_id", "reports", "inspection_id"),
            ("ix_reports_status", "reports", "status"),
            ("ix_reports_generated_by", "reports", "generated_by"),
            ("ix_report_files_report_id_format", "report_files", "report_id, format"),
        ]

        for idx_name, tbl_name, col_names in indexes:
            sql_idx = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {tbl_name}({col_names});"
            print(f"[SQL] {sql_idx}")
            conn.execute(text(sql_idx))

    print("=" * 80)
    print("PHASE 2 MIGRATION COMPLETED SUCCESSFULLY.")
    print("=" * 80)


if __name__ == "__main__":
    run_migration()
