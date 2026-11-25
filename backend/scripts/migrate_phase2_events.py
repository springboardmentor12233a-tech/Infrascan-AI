"""Idempotent Migration Script for Phase 2: Real-Time Engine (Events & Tickets).
Prints all executed SQL statements. Safe to run repeatedly.
"""
import sys
from pathlib import Path
from sqlalchemy import text, inspect

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database import engine


def run_migration():
    print("=" * 80)
    print("RUNNING PHASE 2 REAL-TIME EVENTS DATABASE MIGRATION (EVENTS & TICKETS)")
    print("=" * 80)

    dialect = engine.dialect.name
    print(f"Database Dialect: {dialect}")

    with engine.begin() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())

        # 1. events table
        if "events" not in tables:
            print("[SQL] Creating table 'events'...")
            if dialect == "postgresql":
                sql = """
                CREATE TABLE events (
                    event_id BIGSERIAL PRIMARY KEY,
                    type VARCHAR(100) NOT NULL,
                    entity_type VARCHAR(50) NOT NULL,
                    entity_id VARCHAR(100) NOT NULL,
                    audience_json JSONB NOT NULL,
                    payload_json JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                );
                """
            else:
                sql = """
                CREATE TABLE events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type VARCHAR(100) NOT NULL,
                    entity_type VARCHAR(50) NOT NULL,
                    entity_id VARCHAR(100) NOT NULL,
                    audience_json JSON NOT NULL,
                    payload_json JSON NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
                """
            print(sql.strip())
            conn.execute(text(sql))
        else:
            print("  [OK] Table 'events' already exists.")

        # 2. event_tickets table
        if "event_tickets" not in tables:
            print("[SQL] Creating table 'event_tickets'...")
            if dialect == "postgresql":
                sql = """
                CREATE TABLE event_tickets (
                    ticket_id VARCHAR(64) PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    used_at TIMESTAMP WITH TIME ZONE NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                );
                """
            else:
                sql = """
                CREATE TABLE event_tickets (
                    ticket_id VARCHAR(64) PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    expires_at TIMESTAMP NOT NULL,
                    used_at TIMESTAMP NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
                """
            print(sql.strip())
            conn.execute(text(sql))
        else:
            print("  [OK] Table 'event_tickets' already exists.")

        # 3. Create indexes idempotently
        indexes = [
            ("ix_events_created_at", "events", "(created_at)"),
            ("ix_events_type", "events", "(type)"),
            ("ix_events_entity", "events", "(entity_type, entity_id)"),
            ("ix_event_tickets_user_id", "event_tickets", "(user_id)"),
            ("ix_event_tickets_expires_at", "event_tickets", "(expires_at)"),
        ]

        for idx_name, table_name, columns in indexes:
            sql_idx = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name}{columns};"
            print(f"[SQL] {sql_idx}")
            conn.execute(text(sql_idx))

    print("=" * 80)
    print("PHASE 2 REAL-TIME EVENTS MIGRATION COMPLETED SUCCESSFULLY.")
    print("=" * 80)


if __name__ == "__main__":
    run_migration()
