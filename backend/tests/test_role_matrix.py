import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.services.security import hash_password

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_user(db, email, role, password="MatrixPassword123!", is_active=True):
    user = User(
        full_name=f"Test {role}",
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_token(client, email, password="MatrixPassword123!"):
    resp = client.post("/auth/login", data={"username": email, "password": password})
    return resp.json()["access_token"]


def test_generated_role_matrix_routes(client: TestClient, db_session):
    """
    Test role-based access across all 5 roles and anonymous against protected endpoints.
    """
    config_path = Path(__file__).resolve().parent.parent / "app" / "config" / "role_permissions.json"
    with open(config_path, "r", encoding="utf-8") as f:
        perms = json.load(f)

    # Provision one user for each of the 5 roles
    tokens = {}
    for role in perms["roles"]:
        create_user(db_session, f"{role}@matrix.test", role)
        tokens[role] = get_token(client, f"{role}@matrix.test")

    # Key protected test routes mapped to endpoints
    test_endpoints = [
        ("/users", ["admin"]),
        ("/audit-logs", ["admin"]),
        ("/exports/portfolio", ["admin", "manager", "civil_engineer"]),
        ("/notifications", ["admin", "manager", "civil_engineer", "inspector", "maintenance_engineer"]),
    ]

    for endpoint, allowed_roles in test_endpoints:
        # 1. Anonymous request must return 401
        res_anon = client.get(endpoint)
        assert res_anon.status_code == 401, f"Expected 401 for anonymous on {endpoint}, got {res_anon.status_code}"

        # 2. Check each role
        for role, token in tokens.items():
            headers = {"Authorization": f"Bearer {token}"}
            res = client.get(endpoint, headers=headers)
            if role in allowed_roles:
                assert res.status_code in [200, 204], f"Role {role} should be allowed on {endpoint}, got {res.status_code}"
            else:
                assert res.status_code == 403, f"Role {role} should be forbidden on {endpoint}, got {res.status_code}"


def test_registration_role_tampering_blocked(client: TestClient, db_session):
    """
    Ensure user registration cannot assign admin or manager role (mass assignment protection).
    """
    res = client.post("/auth/register", json={
        "full_name": "Tamper Test",
        "email": "tamper@example.com",
        "password": "SecurePassword123!",
        "role": "admin",
    })
    assert res.status_code == 201
    assert res.json()["role"] == "inspector"


def test_last_admin_protection(client: TestClient, db_session):
    """
    Ensure the last active administrator cannot be demoted or deactivated.
    """
    admin = create_user(db_session, "sole.admin@matrix.test", "admin")
    admin_token = get_token(client, "sole.admin@matrix.test")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Attempt to demote sole admin to inspector
    res_demote = client.put(f"/users/{admin.user_id}/role", json={"role": "inspector"}, headers=headers)
    assert res_demote.status_code == 400
    assert "Cannot demote the last active administrator" in res_demote.json()["detail"]

    # Attempt to deactivate sole admin
    res_deact = client.put(f"/users/{admin.user_id}/active", json={"is_active": False}, headers=headers)
    assert res_deact.status_code == 400
    assert "Administrators cannot deactivate their own account" in res_deact.json()["detail"]


def test_role_change_takes_effect_immediately(client: TestClient, db_session):
    """
    Verify that an admin changing another user's role takes effect on their next request.
    """
    admin = create_user(db_session, "root.admin@matrix.test", "admin")
    target = create_user(db_session, "target.user@matrix.test", "inspector")

    admin_token = get_token(client, "root.admin@matrix.test")
    target_token = get_token(client, "target.user@matrix.test")

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    target_headers = {"Authorization": f"Bearer {target_token}"}

    # Target (inspector) cannot access portfolio export
    assert client.get("/exports/portfolio", headers=target_headers).status_code == 403

    # Admin promotes target to civil_engineer
    res_promo = client.put(f"/users/{target.user_id}/role", json={"role": "civil_engineer"}, headers=admin_headers)
    assert res_promo.status_code == 200
    assert res_promo.json()["role"] == "civil_engineer"

    # In DB user.role is now civil_engineer. get_current_user reads directly from DB for each request.
    res_reports = client.get("/exports/portfolio", headers=target_headers)
    assert res_reports.status_code == 200
