"""Idempotent Migration Script for Phase 1: Authentication, Sessions & Security.
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
    print("RUNNING PHASE 1 DATABASE MIGRATION (SESSIONS, RESET TOKENS, LOGIN ATTEMPTS)")
    print("=" * 80)

    dialect = engine.dialect.name
    print(f"Database Dialect: {dialect}")

    with engine.begin() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())

        # 1. sessions table
        if "sessions" not in tables:
            print("[SQL] Creating table 'sessions'...")
            if dialect == "postgresql":
                sql = """
                CREATE TABLE sessions (
                    session_id VARCHAR(36) PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    token_hash VARCHAR(128) NOT NULL,
                    family_id VARCHAR(36) NOT NULL,
                    user_agent VARCHAR(500) NULL,
                    ip VARCHAR(100) NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    revoked_at TIMESTAMP WITH TIME ZONE NULL
                );
                """
            else:
                sql = """
                CREATE TABLE sessions (
                    session_id VARCHAR(36) PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    token_hash VARCHAR(128) NOT NULL,
                    family_id VARCHAR(36) NOT NULL,
                    user_agent VARCHAR(500) NULL,
                    ip VARCHAR(100) NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    revoked_at TIMESTAMP NULL
                );
                """
            print(sql.strip())
            conn.execute(text(sql))
        else:
            print("  [OK] Table 'sessions' already exists.")

        # 2. password_reset_tokens table
        if "password_reset_tokens" not in tables:
            print("[SQL] Creating table 'password_reset_tokens'...")
            if dialect == "postgresql":
                sql = """
                CREATE TABLE password_reset_tokens (
                    token_id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    token_hash VARCHAR(128) NOT NULL UNIQUE,
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    used_at TIMESTAMP WITH TIME ZONE NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                );
                """
            else:
                sql = """
                CREATE TABLE password_reset_tokens (
                    token_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    token_hash VARCHAR(128) NOT NULL UNIQUE,
                    expires_at TIMESTAMP NOT NULL,
                    used_at TIMESTAMP NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
                """
            print(sql.strip())
            conn.execute(text(sql))
        else:
            print("  [OK] Table 'password_reset_tokens' already exists.")

        # 3. login_attempts table
        if "login_attempts" not in tables:
            print("[SQL] Creating table 'login_attempts'...")
            if dialect == "postgresql":
                sql = """
                CREATE TABLE login_attempts (
                    attempt_id SERIAL PRIMARY KEY,
                    email VARCHAR(255) NULL,
                    ip_address VARCHAR(100) NULL,
                    success BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                );
                """
            else:
                sql = """
                CREATE TABLE login_attempts (
                    attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email VARCHAR(255) NULL,
                    ip_address VARCHAR(100) NULL,
                    success BOOLEAN NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
                """
            print(sql.strip())
            conn.execute(text(sql))
        else:
            print("  [OK] Table 'login_attempts' already exists.")

        # 4. Indexes (idempotent)
        indexes = [
            ("ix_sessions_user_id", "sessions", "user_id"),
            ("ix_sessions_token_hash", "sessions", "token_hash"),
            ("ix_sessions_family_id", "sessions", "family_id"),
            ("ix_password_reset_tokens_user_id", "password_reset_tokens", "user_id"),
            ("ix_password_reset_tokens_token_hash", "password_reset_tokens", "token_hash"),
            ("ix_login_attempts_email_created", "login_attempts", "email, created_at"),
            ("ix_login_attempts_ip_created", "login_attempts", "ip_address, created_at"),
        ]

        for idx_name, tbl_name, col_names in indexes:
            sql_idx = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {tbl_name}({col_names});"
            print(f"[SQL] {sql_idx}")
            conn.execute(text(sql_idx))

    print("=" * 80)
    print("PHASE 1 MIGRATION COMPLETED SUCCESSFULLY.")
    print("=" * 80)


if __name__ == "__main__":
    run_migration()
