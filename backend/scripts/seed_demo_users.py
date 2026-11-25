"""Development-only script to seed one demo user per role with randomly generated passwords.
Attaches demo markers for clean teardown. Refuses to run in production.
"""
import secrets
import string
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models.demo import DemoMarker
from app.models.user import ALLOWED_ROLES, User
from app.services.audit import create_audit_log
from app.services.security import hash_password


def generate_random_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    # Ensure at least one upper, lower, digit, symbol
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in pwd)
            and any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in "!@#$%^&*" for c in pwd)):
            return pwd


def seed_demo_users():
    print("=" * 80)
    print("SEEDING DEMO USERS (DEVELOPMENT ONLY)")
    print("=" * 80)

    if getattr(settings, "ENV", "development").lower() == "production":
        print("FATAL ERROR: seed_demo_users.py is strictly forbidden in production environment.")
        sys.exit(1)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    roles_to_seed = [
        ("admin", "Demo Admin", "demo.admin@infrascan.local"),
        ("civil_engineer", "Demo Civil Engineer", "demo.engineer@infrascan.local"),
        ("inspector", "Demo Inspector", "demo.inspector@infrascan.local"),
        ("maintenance_engineer", "Demo Maintenance Engineer", "demo.maintenance@infrascan.local"),
        ("manager", "Demo Manager", "demo.manager@infrascan.local"),
    ]

    print("\nPROVISIONING DEMO ACCOUNTS...")
    print(f"{'Role':<24} {'Email':<35} {'Status'}")
    print("-" * 80)

    creds_lines = [
        "# InfraScan Local Demo Account Credentials (DO NOT COMMIT)",
        f"# Generated at {secrets.token_hex(4)}",
        "# -------------------------------------------------------------",
    ]

    try:
        for role, name, email in roles_to_seed:
            pwd = generate_random_password(14)
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    full_name=name,
                    email=email,
                    password_hash=hash_password(pwd),
                    role=role,
                    is_active=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)

                # Attach demo marker
                marker = DemoMarker(entity_type="user", entity_id=str(user.user_id))
                db.add(marker)
                db.commit()

                create_audit_log(
                    db=db,
                    action="demo_user_created",
                    user_id=user.user_id,
                    entity_type="user",
                    entity_id=str(user.user_id),
                )
                status = "CREATED"
            else:
                user.password_hash = hash_password(pwd)
                user.is_active = True
                user.role = role
                user.full_name = name
                db.commit()
                status = "UPDATED"

            print(f"{role:<24} {email:<35} {status}")
            creds_lines.append(f"{role}:{email}:{pwd}")

        # Write credentials once to gitignored file docs/final/demo_accounts.local.txt
        output_file = Path(r"D:\Infosys springboards\docs\final\demo_accounts.local.txt")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("\n".join(creds_lines) + "\n", encoding="utf-8")
        print(f"\n[+] Credentials written ONCE to gitignored file: {output_file}")
        print("[+] Passwords not logged to console for security compliance.")
    finally:
        db.close()

    print("=" * 80)
    print("DEMO USERS SEEDING COMPLETE.")
    print("=" * 80)


if __name__ == "__main__":
    seed_demo_users()
