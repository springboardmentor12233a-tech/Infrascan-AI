import jwt
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.models.session import UserSession, PasswordResetToken, LoginAttempt
from app.services.security import hash_password, create_access_token
from app.config import settings

# Test database
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


def create_test_user(db_session, email="user@example.com", role="inspector", password="SecurePassword123!", is_active=True):
    user = User(
        full_name="Test User",
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# 1. Refresh token rotation & reuse detection
def test_refresh_token_rotation_and_reuse_detection(client: TestClient, db_session):
    user = create_test_user(db_session, email="rotate@example.com", password="SecurePassword123!")

    # Login to get refresh token
    login_resp = client.post("/auth/login", data={"username": "rotate@example.com", "password": "SecurePassword123!"})
    assert login_resp.status_code == 200
    data1 = login_resp.json()
    refresh_token_1 = data1["refresh_token"]
    assert refresh_token_1 is not None

    # Rotate refresh token
    refresh_resp = client.post("/auth/refresh", json={"refresh_token": refresh_token_1})
    assert refresh_resp.status_code == 200
    data2 = refresh_resp.json()
    refresh_token_2 = data2["refresh_token"]
    assert refresh_token_2 != refresh_token_1

    # Attempting to reuse old refresh token 1 must fail and revoke family
    reuse_resp = client.post("/auth/refresh", json={"refresh_token": refresh_token_1})
    assert reuse_resp.status_code == 401
    assert "reuse detected" in reuse_resp.json()["detail"].lower()

    # Now refresh token 2 must also be revoked because the entire family was terminated
    after_reuse_resp = client.post("/auth/refresh", json={"refresh_token": refresh_token_2})
    assert after_reuse_resp.status_code == 401


# 2. Lockout after 5 failed attempts in 15 minutes
def test_account_lockout_after_repeated_failures(client: TestClient, db_session):
    create_test_user(db_session, email="victim@example.com", password="CorrectPassword123!")

    # 4 failed attempts should return 400 Incorrect email or password
    for i in range(4):
        res = client.post("/auth/login", data={"username": "victim@example.com", "password": "WrongPassword!"})
        assert res.status_code == 400
        assert res.json()["detail"] == "Incorrect email or password"

    # 5th failed attempt triggers lockout
    res5 = client.post("/auth/login", data={"username": "victim@example.com", "password": "WrongPassword!"})
    assert res5.status_code == 400

    # Even with correct password, account is now locked
    locked_res = client.post("/auth/login", data={"username": "victim@example.com", "password": "CorrectPassword123!"})
    assert locked_res.status_code == 400
    assert "locked" in locked_res.json()["detail"].lower()


# 3. Password policy: min length & common blocklist
def test_password_policy_enforcement(client: TestClient, db_session):
    # Short password (< 10 chars) rejected
    res_short = client.post("/auth/register", json={
        "full_name": "Short Pass",
        "email": "short@example.com",
        "password": "Pass123",
    })
    assert res_short.status_code in (400, 422)

    # Common password from blocklist rejected
    res_block = client.post("/auth/register", json={
        "full_name": "Blocklist User",
        "email": "block@example.com",
        "password": "password1234",
    })
    assert res_block.status_code == 400
    assert "too common" in res_block.json()["detail"].lower()


# 4. Forgot & Reset password flow with single-use token
def test_forgot_and_reset_password_flow(client: TestClient, db_session):
    user = create_test_user(db_session, email="reset@example.com", password="OldPassword123!")

    # Forgot password gives generic message
    res_forgot = client.post("/auth/forgot-password", json={"email": "reset@example.com"})
    assert res_forgot.status_code == 200
    assert "instructions have been sent" in res_forgot.json()["message"]

    # Unknown email gives identical message
    res_unknown = client.post("/auth/forgot-password", json={"email": "nonexistent@example.com"})
    assert res_unknown.status_code == 200
    assert res_unknown.json()["message"] == res_forgot.json()["message"]

    # Check reset token created in DB
    reset_record = db_session.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.user_id).first()
    assert reset_record is not None

    # Perform password reset using token
    from app.services.session_service import create_password_reset_token
    token_str = create_password_reset_token(db_session, user.user_id)

    res_reset = client.post("/auth/reset-password", json={
        "token": token_str,
        "new_password": "BrandNewPassword123!",
    })
    assert res_reset.status_code == 200
    assert "reset successfully" in res_reset.json()["message"]

    # Reusing the reset token must fail
    res_reuse = client.post("/auth/reset-password", json={
        "token": token_str,
        "new_password": "BrandNewPassword123!",
    })
    assert res_reuse.status_code == 400

    # Old password fails, new password succeeds
    login_old = client.post("/auth/login", data={"username": "reset@example.com", "password": "OldPassword123!"})
    assert login_old.status_code == 400

    login_new = client.post("/auth/login", data={"username": "reset@example.com", "password": "BrandNewPassword123!"})
    assert login_new.status_code == 200


# 5. Last active administrator protection
def test_last_active_admin_protection(client: TestClient, db_session):
    admin = create_test_user(db_session, email="sole.admin@example.com", role="admin", password="AdminPassword123!")

    login_resp = client.post("/auth/login", data={"username": "sole.admin@example.com", "password": "AdminPassword123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Demote sole admin should be refused
    res_demote = client.put(f"/users/{admin.user_id}/role", json={"role": "inspector"}, headers=headers)
    assert res_demote.status_code == 400
    assert "cannot demote" in res_demote.json()["detail"].lower()

    # Deactivate sole admin / self should be refused
    res_deact = client.put(f"/users/{admin.user_id}/active", json={"is_active": False}, headers=headers)
    assert res_deact.status_code == 400
    assert "cannot deactivate" in res_deact.json()["detail"].lower()


# 6. Tampered, expired, and alg: "none" tokens rejected
def test_token_tamper_expiry_and_alg_none(client: TestClient, db_session):
    create_test_user(db_session, email="tokencheck@example.com", role="inspector")

    # 1. Tampered token
    res_tamper = client.get("/users/me", headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.invalid.signature"})
    assert res_tamper.status_code == 401

    # 2. Expired token
    expired_token = jwt.encode(
        {"sub": "tokencheck@example.com", "exp": datetime.now(timezone.utc) - timedelta(minutes=5), "iat": datetime.now(timezone.utc) - timedelta(minutes=15), "type": "access"},
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    res_exp = client.get("/users/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res_exp.status_code == 401

    # 3. alg none token
    alg_none_token = jwt.encode(
        {"sub": "tokencheck@example.com", "exp": datetime.now(timezone.utc) + timedelta(minutes=15), "iat": datetime.now(timezone.utc), "type": "access"},
        key="",
        algorithm="none"
    )
    res_none = client.get("/users/me", headers={"Authorization": f"Bearer {alg_none_token}"})
    assert res_none.status_code == 401


# 7. Mass assignment protection on registration
def test_mass_assignment_protection(client: TestClient, db_session):
    # Register trying to set role="admin" and is_active=False
    res = client.post("/auth/register", json={
        "full_name": "Sneaky User",
        "email": "sneaky@example.com",
        "password": "SneakyPassword123!",
        "role": "admin",
        "is_active": False,
    })
    assert res.status_code == 201
    user_data = res.json()
    assert user_data["role"] == "inspector"  # Must remain inspector!
    assert user_data["is_active"] is True


# 8. Role Matrix verification
def test_role_matrix_access_control(client: TestClient, db_session):
    admin = create_test_user(db_session, email="admin.matrix@example.com", role="admin", password="AdminPassword123!")
    inspector = create_test_user(db_session, email="insp.matrix@example.com", role="inspector", password="InspPassword123!")

    admin_token = client.post("/auth/login", data={"username": "admin.matrix@example.com", "password": "AdminPassword123!"}).json()["access_token"]
    insp_token = client.post("/auth/login", data={"username": "insp.matrix@example.com", "password": "InspPassword123!"}).json()["access_token"]

    # GET /users
    # Anonymous -> 401
    assert client.get("/users").status_code == 401
    # Inspector -> 403
    assert client.get("/users", headers={"Authorization": f"Bearer {insp_token}"}).status_code == 403
    # Admin -> 200
    assert client.get("/users", headers={"Authorization": f"Bearer {admin_token}"}).status_code == 200

    # GET /audit-logs
    # Anonymous -> 401
    assert client.get("/audit-logs").status_code == 401
    # Inspector -> 403
    assert client.get("/audit-logs", headers={"Authorization": f"Bearer {insp_token}"}).status_code == 403
    # Admin -> 200
    assert client.get("/audit-logs", headers={"Authorization": f"Bearer {admin_token}"}).status_code == 200
