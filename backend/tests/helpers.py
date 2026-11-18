from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User


def get_user_token(client: TestClient, db_session, role_name: str, email_prefix: str = "user"):
    """Create a user in the test database and return a real login JWT.

    Privileged roles are inserted directly. Public registration cannot
    self-assign Administrator or Infrastructure Manager.
    """
    role = db_session.query(Role).filter(Role.name == role_name).first()
    if role is None:
        raise RuntimeError(f"Role not seeded: {role_name}")
    email = f"{email_prefix}_{role_name.lower().replace(' ', '_')}@test.com"
    password = "TestPassword123!"
    user = db_session.query(User).filter(User.email == email).first()
    if user is None:
        user = User(
            email=email,
            full_name=f"Test {role_name}",
            password_hash=hash_password(password),
            role_id=role.id,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
    login_res = client.post("/auth/login", data={"username": email, "password": password})
    assert login_res.status_code == 200, login_res.text
    return login_res.json()["access_token"]
