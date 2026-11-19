import getpass
from database import get_connection
from auth import hash_password

name = input("Enter user name: ").strip()
email = input("Enter user email: ").strip().lower()
password = getpass.getpass("Enter password: ")

if not name or not email or len(password) < 8:
    print("Enter valid details. Password must be at least 8 characters.")
else:
    connection = get_connection()
    try:
        existing = connection.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()

        if existing:
            print("This email is already registered.")
        else:
            connection.execute(
                """
                INSERT INTO users (full_name, email, hashed_password, role)
                VALUES (?, ?, ?, ?)
                """,
                (name, email, hash_password(password), "User"),
            )
            connection.commit()
            print("User account created successfully!")

    finally:
        connection.close()