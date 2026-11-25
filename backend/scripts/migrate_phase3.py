"""Phase 3 Database Migration: Notifications and Preferences Tables.

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
    print("RUNNING PHASE 3 DATABASE MIGRATION (NOTIFICATIONS & PREFERENCES)")
    print("=" * 80)

    dialect_name = engine.dialect.name
    print(f"Database Dialect: {dialect_name}")

    with engine.begin() as conn:
        inspector = inspect(conn)
        tables = inspector.get_table_names()

        # 1. Create 'notifications' table
        if "notifications" not in tables:
            print("[SQL] Creating table 'notifications'...")
            if dialect_name == "postgresql":
                sql = """
                CREATE TABLE notifications (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    type VARCHAR(50) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    body TEXT NOT NULL,
                    entity_type VARCHAR(50),
                    entity_id VARCHAR(50),
                    read_at TIMESTAMP WITH TIME ZONE,
                    email_sent BOOLEAN NOT NULL DEFAULT FALSE,
                    email_sent_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
                """
            else:
                sql = """
                CREATE TABLE notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    type VARCHAR(50) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    body TEXT NOT NULL,
                    entity_type VARCHAR(50),
                    entity_id VARCHAR(50),
                    read_at TIMESTAMP,
                    email_sent BOOLEAN NOT NULL DEFAULT 0,
                    email_sent_at TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            print(f"[SQL] {sql.strip()}")
            conn.execute(text(sql))
            print("  [OK] Table 'notifications' created.")
        else:
            print("  [OK] Table 'notifications' already exists.")

        # 2. Create 'notification_preferences' table
        if "notification_preferences" not in tables:
            print("[SQL] Creating table 'notification_preferences'...")
            if dialect_name == "postgresql":
                sql = """
                CREATE TABLE notification_preferences (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
                    in_app_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    email_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    min_severity VARCHAR(30) NOT NULL DEFAULT 'low',
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
                """
            else:
                sql = """
                CREATE TABLE notification_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
                    in_app_enabled BOOLEAN NOT NULL DEFAULT 1,
                    email_enabled BOOLEAN NOT NULL DEFAULT 1,
                    min_severity VARCHAR(30) NOT NULL DEFAULT 'low',
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            print(f"[SQL] {sql.strip()}")
            conn.execute(text(sql))
            print("  [OK] Table 'notification_preferences' created.")
        else:
            print("  [OK] Table 'notification_preferences' already exists.")

        # 3. Create indexes
        indexes = [
            ("ix_notifications_user_id", "notifications", "user_id"),
            ("ix_notifications_type", "notifications", "type"),
            ("ix_notifications_read_at", "notifications", "read_at"),
            ("ix_notifications_created_at", "notifications", "created_at"),
            ("ix_notification_preferences_user_id", "notification_preferences", "user_id"),
        ]

        for idx_name, table_name, col_name in indexes:
            sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name}({col_name});"
            print(f"[SQL] {sql}")
            conn.execute(text(sql))

    print("=" * 80)
    print("PHASE 3 MIGRATION COMPLETED SUCCESSFULLY.")
    print("=" * 80)


if __name__ == "__main__":
    run_migration()
