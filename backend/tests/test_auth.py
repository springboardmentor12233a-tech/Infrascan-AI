from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.services.security import hash_password

# Use an in-memory SQLite database for isolated test execution
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    # Setup test tables
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    # Override get_db dependency with test database session
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# 1. Test user registration (auto role "inspector")
def test_register(client: TestClient):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "John Inspector",
            "email": "john@example.com",
            "password": "Password123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "john@example.com"
    assert data["role"] == "inspector"  # User cannot choose role
    assert data["is_active"] is True
    assert "user_id" in data


# 2. Test user login returns access token and role
def test_login(client: TestClient):
    # First register user
    client.post(
        "/auth/register",
        json={
            "full_name": "Jane Inspector",
            "email": "jane@example.com",
            "password": "Password123",
        },
    )

    # Login using OAuth2 form data
    response = client.post(
        "/auth/login",
        data={"username": "jane@example.com", "password": "Password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "inspector"


# 3. Test wrong password returns 400 with same generic error as wrong email
def test_wrong_password(client: TestClient):
    client.post(
        "/auth/register",
        json={
            "full_name": "Bob Inspector",
            "email": "bob@example.com",
            "password": "Password123",
        },
    )

    # Attempt login with wrong password
    wrong_pass_resp = client.post(
        "/auth/login",
        data={"username": "bob@example.com", "password": "WrongPassword999"},
    )
    assert wrong_pass_resp.status_code == 400
    assert wrong_pass_resp.json()["detail"] == "Incorrect email or password"

    # Attempt login with non-existent email
    wrong_email_resp = client.post(
        "/auth/login",
        data={"username": "ghost@example.com", "password": "Password123"},
    )
    assert wrong_email_resp.status_code == 400
    assert wrong_email_resp.json()["detail"] == "Incorrect email or password"


# 4. Test inspector role is blocked from GET /users (returns 403)
def test_inspector_blocked_from_get_users(client: TestClient):
    client.post(
        "/auth/register",
        json={
            "full_name": "Regular User",
            "email": "regular@example.com",
            "password": "Password123",
        },
    )

    login_resp = client.post(
        "/auth/login",
        data={"username": "regular@example.com", "password": "Password123"},
    )
    token = login_resp.json()["access_token"]

    # Inspector attempts to call admin-only GET /users
    users_resp = client.get(
        "/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert users_resp.status_code == 403
    assert "Insufficient permissions" in users_resp.json()["detail"] or "not permitted" in users_resp.json()["detail"]


# 5. Test admin role is allowed to access GET /users (returns 200)
def test_admin_allowed_get_users(client: TestClient, db_session):
    # Directly seed an admin user in the test database
    admin = User(
        full_name="Admin User",
        email="admin@example.com",
        password_hash=hash_password("AdminPass123"),
        role="admin",
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    # Login as admin
    login_resp = client.post(
        "/auth/login",
        data={"username": "admin@example.com", "password": "AdminPass123"},
    )
    token = login_resp.json()["access_token"]

    # Admin requests GET /users
    users_resp = client.get(
        "/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert users_resp.status_code == 200
    users_list = users_resp.json()
    assert isinstance(users_list, list)
    assert len(users_list) == 1
    assert users_list[0]["email"] == "admin@example.com"
