"""
Database migration script to add image_scales table and scale/uncertainty columns to crack_measurements.
Safe and idempotent across PostgreSQL and SQLite databases.
"""

from sqlalchemy import inspect, text
from app.database import Base, engine
from app.models.analysis import ImageScale, CrackMeasurement


def run_migration():
    # 1. Ensure image_scales table exists
    Base.metadata.create_all(bind=engine, tables=[ImageScale.__table__, CrackMeasurement.__table__])

    # 2. Check and add columns to crack_measurements if needed
    inspector = inspect(engine)
    existing_columns = {col["name"] for col in inspector.get_columns("crack_measurements")}

    columns_to_add = [
        ("scale_id", "INTEGER REFERENCES image_scales(scale_id) ON DELETE SET NULL"),
        ("length_mm_uncertainty", "FLOAT"),
        ("width_mm_uncertainty", "FLOAT"),
        ("measurement_note", "TEXT"),
    ]

    is_postgres = engine.dialect.name == "postgresql"

    with engine.begin() as conn:
        for col_name, col_def in columns_to_add:
            if col_name not in existing_columns:
                if is_postgres:
                    stmt = f"ALTER TABLE crack_measurements ADD COLUMN IF NOT EXISTS {col_name} {col_def};"
                else:
                    stmt = f"ALTER TABLE crack_measurements ADD COLUMN {col_name} {col_def};"
                print(f"Executing: {stmt}")
                conn.execute(text(stmt))
            else:
                print(f"Column '{col_name}' already exists in 'crack_measurements'.")

    print("Migration completed: 'image_scales' table and 'crack_measurements' columns verified successfully!")


if __name__ == "__main__":
    run_migration()

