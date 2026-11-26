import sys, os
import argparse
import sqlite3
from datetime import datetime
from database import engine, SessionLocal, Base, DB_PATH
from models import User, Inspection
from auth import get_password_hash

def migrate_database():
    """Safely adds user_id column to inspections table if not already present."""
    Base.metadata.create_all(bind=engine)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(inspections);")
    cols = [col[1] for col in cursor.fetchall()]
    if "user_id" not in cols:
        print("Migrating database: adding 'user_id' column to 'inspections' table...")
        cursor.execute("ALTER TABLE inspections ADD COLUMN user_id INTEGER REFERENCES users(id);")
        conn.commit()
        print("Migration complete: 'user_id' column added.")
    else:
        print("Database schema verified: 'user_id' already present in 'inspections'.")
    conn.close()

def create_admin_user(username: str, email: str, password: str, full_name: str = "System Administrator"):
    migrate_database()
    db = SessionLocal()
    try:
        existing = db.query(User).filter((User.username == username) | (User.email == email)).first()
        if existing:
            if existing.role != "admin":
                print(f"Upgrading existing user '{existing.username}' to 'admin' role...")
                existing.role = "admin"
                existing.status = "active"
                if password:
                    existing.hashed_password = get_password_hash(password)
                db.commit()
                print(f"User '{existing.username}' is now an Administrator.")
                return existing
            else:
                print(f"Admin user '{existing.username}' already exists. Updating password...")
                if password:
                    existing.hashed_password = get_password_hash(password)
                    db.commit()
                    print("Password updated successfully.")
                return existing

        admin = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role="admin",
            status="active",
            created_at=datetime.utcnow()
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"SUCCESS: Initial Administrator '{admin.username}' ({admin.email}) created successfully (ID: {admin.id}).")
        return admin
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap or create an InfraScan Administrator account.")
    parser.add_argument("--username", required=True, help="Admin username")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--password", required=True, help="Admin password")
    parser.add_argument("--fullname", default="System Administrator", help="Admin full name")

    args = parser.parse_args()
    create_admin_user(args.username, args.email, args.password, args.fullname)
