import getpass

from database import get_connection
from auth import hash_password


def create_admin():
    print("\n--- InfraScan Admin Setup ---")

    full_name = input("Enter administrator name: ").strip()
    email = input("Enter administrator email: ").strip().lower()
    password = getpass.getpass("Enter administrator password: ")
    confirm_password = getpass.getpass("Confirm password: ")

    if not full_name or not email or not password:
        print("All fields are required.")
        return

    if password != confirm_password:
        print("Passwords do not match.")
        return

    if len(password) < 8:
        print("Password must contain at least 8 characters.")
        return

    connection = get_connection()

    try:
        existing_admin = connection.execute(
            "SELECT id FROM users WHERE role = ?",
            ("Admin",),
        ).fetchone()

        if existing_admin:
            print("An Admin account already exists.")
            return

        connection.execute(
            """
            INSERT INTO users
            (full_name, email, hashed_password, role)
            VALUES (?, ?, ?, ?)
            """,
            (
                full_name,
                email,
                hash_password(password),
                "Admin",
            ),
        )

        connection.commit()
        print("\nAdmin account created successfully!")

    except Exception as error:
        connection.rollback()
        print(f"Could not create Admin: {error}")

    finally:
        connection.close()


if __name__ == "__main__":
    create_admin()