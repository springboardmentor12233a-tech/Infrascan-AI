"""
Database migration script to add image preprocessing columns.
Safe and idempotent: uses ADD COLUMN IF NOT EXISTS.
"""

from sqlalchemy import text
from app.database import engine


def run_migration():
    statements = [
        "ALTER TABLE images ADD COLUMN IF NOT EXISTS processed_file_path VARCHAR(255);",
        "ALTER TABLE images ADD COLUMN IF NOT EXISTS preprocess_status VARCHAR(20) DEFAULT 'not_run';",
        "ALTER TABLE images ADD COLUMN IF NOT EXISTS preprocess_steps TEXT;",
        "ALTER TABLE images ADD COLUMN IF NOT EXISTS preprocessed_at TIMESTAMP WITH TIME ZONE;",
    ]

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
    print("Preprocess columns successfully verified / added to 'images' table!")


if __name__ == "__main__":
    run_migration()
