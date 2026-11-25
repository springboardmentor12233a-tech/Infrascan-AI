"""First-run script to bootstrap the initial system administrator for InfraScan.
Supports CLI arguments or interactive prompts. Never uses a default password.
"""
import argparse
import getpass
import sys
from pathlib import Path

# Add backend root to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database import Base, SessionLocal, engine
from app.models.user import User
from app.services.audit import create_audit_log
from app.services.security import hash_password, validate_password_policy


def bootstrap_admin():
    parser = argparse.ArgumentParser(description="Bootstrap initial InfraScan Administrator.")
    parser.add_argument("--email", type=str, help="Admin email address")
    parser.add_argument("--password", type=str, help="Admin password (at least 10 characters)")
    parser.add_argument("--name", type=str, default="System Administrator", help="Admin full name")
    parser.add_argument("--force", action="store_true", help="Force creation of an additional administrator if one already exists")

    args = parser.parse_args()

    email = args.email
    if not email:
        try:
            email = input("Enter administrator email: ").strip()
        except EOFError:
            pass

    if not email or "@" not in email:
        print("Error: A valid email address is required.")
        sys.exit(1)
    email = email.lower().strip()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Refuse to create a second admin unless --force is passed
        existing_admins = db.query(User).filter(User.role == "admin", User.is_active == True).count()
        existing_target_user = db.query(User).filter(User.email == email).first()

        if existing_admins > 0 and not args.force:
            # If the user being bootstrapped is already an admin, updating is allowed
            if not (existing_target_user and existing_target_user.role == "admin"):
                print("Error: An active administrator already exists. Refusing to create another admin unless --force is specified.")
                sys.exit(1)

        password = args.password
        if not password:
            try:
                password = getpass.getpass("Enter administrator password (min 10 characters, never default): ").strip()
            except EOFError:
                pass

        if not password:
            print("Error: Password cannot be empty.")
            sys.exit(1)

        try:
            validate_password_policy(password)
        except Exception as e:
            print(f"Error: {getattr(e, 'detail', str(e))}")
            sys.exit(1)

        full_name = args.name.strip()

        existing_user = existing_target_user
        if existing_user:
            if existing_user.role == "admin" and existing_user.is_active:
                print(f"Notice: User {email} is already an active administrator.")
                return
            existing_user.role = "admin"
            existing_user.is_active = True
            existing_user.password_hash = hash_password(password)
            db.commit()
            print(f"Success: Existing user {email} promoted to administrator with updated password.")
            create_audit_log(
                db=db,
                action="bootstrap_admin_promoted",
                user_id=existing_user.user_id,
                entity_type="user",
                entity_id=str(existing_user.user_id),
            )
            return

        new_admin = User(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
        )
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)

        create_audit_log(
            db=db,
            action="bootstrap_admin_created",
            user_id=new_admin.user_id,
            entity_type="user",
            entity_id=str(new_admin.user_id),
        )
        print(f"Success: Initial administrator account {email} created successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    bootstrap_admin()
