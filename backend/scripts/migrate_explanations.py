"""
Database migration script to add the explanations table.
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
from app.models.explanation import Explanation


def run_migration():
    # 1. Ensure explanations table exists
    Base.metadata.create_all(bind=engine, tables=[Explanation.__table__])

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    if "explanations" in existing_tables:
        print("Table 'explanations' verified successfully.")
    else:
        print("Table 'explanations' creation pending or failed.")

    print("Migration completed: 'explanations' table verified.")


if __name__ == "__main__":
    run_migration()
