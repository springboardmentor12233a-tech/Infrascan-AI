import argparse
import getpass
from pathlib import Path
import sys

# Ensure backend root is on Python path so app.* modules can be imported
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import Base, SessionLocal, engine
from app.models.user import User
from app.services.audit import create_audit_log
from app.services.security import hash_password


def seed_admin():
    parser = argparse.ArgumentParser(description="Create the first admin user for InfraScan.")
    parser.add_argument("--email", type=str, help="Admin email address")
    parser.add_argument("--password", type=str, help="Admin password (at least 8 characters)")
    parser.add_argument("--name", type=str, default="System Administrator", help="Admin full name")

    args = parser.parse_args()

    # Read email from command line or prompt interactively
    email = args.email
    if not email:
        email = input("Enter admin email: ").strip()

    if not email or "@" not in email:
        print("Error: A valid email address is required.")
        sys.exit(1)

    # Read password from command line or prompt interactively
    password = args.password
    if not password:
        password = getpass.getpass("Enter admin password (min 8 chars): ").strip()

    if len(password) < 8:
        print("Error: Password must be at least 8 characters long.")
        sys.exit(1)

    full_name = args.name

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"User with email '{email}' already exists. Updating role to admin...")
            existing_user.role = "admin"
            existing_user.is_active = True
            existing_user.password_hash = hash_password(password)
            db.commit()
            db.refresh(existing_user)
            print(f"Successfully updated user '{email}' to admin!")
            create_audit_log(
                db=db,
                action="seed_admin_updated",
                user_id=existing_user.user_id,
                entity_type="user",
                entity_id=str(existing_user.user_id),
            )
            return

        # Create new admin user
        admin_user = User(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        # Audit log entry
        create_audit_log(
            db=db,
            action="seed_admin_created",
            user_id=admin_user.user_id,
            entity_type="user",
            entity_id=str(admin_user.user_id),
        )

        print(f"Admin user created successfully! ID: {admin_user.user_id}, Email: {admin_user.email}, Role: {admin_user.role}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()
