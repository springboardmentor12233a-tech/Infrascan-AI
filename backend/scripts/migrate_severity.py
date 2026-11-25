"""
Database migration script to add severity_assessments and inspection_severity tables.
Safe and idempotent across PostgreSQL and SQLite databases.
"""

import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import inspect
from app.database import Base, engine
from app.models.severity import SeverityAssessment, InspectionSeverity


def run_migration():
    # 1. Ensure severity_assessments and inspection_severity tables exist
    Base.metadata.create_all(bind=engine, tables=[SeverityAssessment.__table__, InspectionSeverity.__table__])

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    if "severity_assessments" in existing_tables:
        print("Table 'severity_assessments' verified.")
    else:
        print("Table 'severity_assessments' created.")

    if "inspection_severity" in existing_tables:
        print("Table 'inspection_severity' verified.")
    else:
        print("Table 'inspection_severity' created.")

    print("Migration completed: 'severity_assessments' and 'inspection_severity' tables verified successfully!")


if __name__ == "__main__":
    run_migration()
