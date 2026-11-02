from fastapi.testclient import TestClient

from app.models.role import Role


def get_user_token(client: TestClient, db_session, role_name: str, email_prefix: str = "user"):
    role = db_session.query(Role).filter(Role.name == role_name).first()
    email = f"{email_prefix}_{role_name.lower().replace(' ', '_')}@test.com"
    password = "TestPassword123!"
    client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": f"Test {role_name}",
            "password": password,
            "role_id": role.id,
        },
    )
    login_res = client.post("/auth/login", data={"username": email, "password": password})
    return login_res.json()["access_token"]
