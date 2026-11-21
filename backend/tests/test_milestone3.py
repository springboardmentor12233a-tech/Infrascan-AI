"""Milestone 3: JWT creation, expiry, and role authorization.

These tests use the real login endpoint. They do not print tokens.
"""

import io
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from jose import jwt
from PIL import Image

from app.config import settings
from app.core.security import (
    ExpiredSignatureError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.infrastructure_asset import InfrastructureAsset
from app.models.role import Role
from app.models.user import User
from tests.helpers import get_user_token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_password_hash_is_not_plaintext():
    hashed = hash_password("Password123!")
    assert hashed != "Password123!"
    assert hashed.startswith("$2")
    assert verify_password("Password123!", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_access_token_has_subject_role_and_expiry():
    token = create_access_token({"sub": "7", "role": "Infrastructure Inspector"})
    payload = decode_access_token(token)
    assert payload["sub"] == "7"
    assert payload["role"] == "Infrastructure Inspector"
    assert "exp" in payload


def test_expired_token_is_rejected(client: TestClient, db_session):
    token = get_user_token(client, db_session, "Infrastructure Inspector", "expired_m3")
    user = db_session.query(User).filter(User.email.like("expired_m3_%")).one()
    expired = jwt.encode(
        {
            "sub": str(user.id),
            "role": "Infrastructure Inspector",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    response = client.get("/auth/me", headers=_auth(expired))
    assert response.status_code == 401
    assert response.json()["detail"] == "Token has expired"


def test_decode_helper_raises_for_an_expired_token():
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    try:
        decode_access_token(expired)
    except ExpiredSignatureError:
        return
    raise AssertionError("expired token was accepted")


def test_invalid_token_is_rejected(client: TestClient):
    response = client.get("/auth/me", headers=_auth("this-is-not-a-jwt"))
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_tampered_token_is_rejected(client: TestClient, db_session):
    token = get_user_token(client, db_session, "Civil Engineer", "tamper_m3")
    tampered = token[:-4] + ("aaaa" if not token.endswith("aaaa") else "bbbb")
    response = client.get("/auth/me", headers=_auth(tampered))
    assert response.status_code == 401


def test_missing_token_is_rejected(client: TestClient):
    me = client.get("/auth/me")
    assets = client.get("/assets/")
    inspections = client.get("/inspections/")
    assert me.status_code == 401
    assert assets.status_code == 401
    assert inspections.status_code == 401


def test_login_returns_profile_and_me_matches(client: TestClient, db_session):
    email = "profile_m3@test.com"
    registered = client.post("/auth/register", json={
        "email": email,
        "full_name": "Profile User",
        "password": "Password123!",
    })
    assert registered.status_code == 201
    assert "password" not in registered.json()
    logged_in = client.post("/auth/login", data={"username": email, "password": "Password123!"})
    assert logged_in.status_code == 200
    body = logged_in.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == email
    assert body["user"]["role"]["name"] == "Civil Engineer"
    me = client.get("/auth/me", headers=_auth(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["id"] == body["user"]["id"]
    assert me.json()["role"]["name"] == "Civil Engineer"


def test_inactive_user_cannot_login_or_reuse_a_token(client: TestClient, db_session):
    token = get_user_token(client, db_session, "Maintenance Engineer", "inactive_m3")
    user = db_session.query(User).filter(User.email.like("inactive_m3_%")).one()
    user.is_active = False
    db_session.commit()
    login = client.post("/auth/login", data={
        "username": user.email,
        "password": "TestPassword123!",
    })
    assert login.status_code == 403
    reused = client.get("/auth/me", headers=_auth(token))
    assert reused.status_code == 403
    assert reused.json()["detail"] == "Inactive user"


def test_public_registration_cannot_claim_privileged_roles(client: TestClient, db_session):
    for role_name in ("Administrator", "Infrastructure Manager"):
        role = db_session.query(Role).filter(Role.name == role_name).one()
        response = client.post("/auth/register", json={
            "email": f"claim_{role.id}@test.com",
            "full_name": "Claimant",
            "password": "Password123!",
            "role_id": role.id,
        })
        assert response.status_code == 403, response.text


def test_anonymous_role_list_hides_privileged_roles(client: TestClient, db_session):
    public = client.get("/auth/roles")
    assert public.status_code == 200
    names = {row["name"] for row in public.json()}
    assert "Administrator" not in names
    assert "Infrastructure Manager" not in names
    assert "Infrastructure Inspector" in names

    admin = get_user_token(client, db_session, "Administrator", "roles_m3")
    private = client.get("/auth/roles", headers=_auth(admin))
    assert private.status_code == 200
    admin_names = {row["name"] for row in private.json()}
    assert "Administrator" in admin_names
    assert "Infrastructure Manager" in admin_names


def test_inspector_permissions(client: TestClient, db_session):
    inspector = get_user_token(client, db_session, "Infrastructure Inspector", "perm_insp_m3")
    manager = get_user_token(client, db_session, "Infrastructure Manager", "perm_mgr_m3")
    inspector_headers = _auth(inspector)
    manager_headers = _auth(manager)

    created = client.post("/assets/", json={
        "asset_code": "M3-INSP-1",
        "name": "Inspector Permission Bridge",
        "type": "Bridge",
    }, headers=manager_headers)
    assert created.status_code == 201
    asset_id = created.json()["id"]

    listed = client.get("/assets/", headers=inspector_headers)
    assert listed.status_code == 200
    assert any(item["id"] == asset_id for item in listed.json()["items"])

    denied_create = client.post("/assets/", json={
        "asset_code": "M3-INSP-DENY",
        "name": "Should Fail",
        "type": "Road",
    }, headers=inspector_headers)
    assert denied_create.status_code == 403

    denied_update = client.put(
        f"/assets/{asset_id}",
        json={"name": "Inspector Edit"},
        headers=inspector_headers,
    )
    assert denied_update.status_code == 403

    denied_delete = client.delete(f"/assets/{asset_id}", headers=inspector_headers)
    assert denied_delete.status_code == 403

    denied_users = client.get("/users/", headers=inspector_headers)
    assert denied_users.status_code == 403

    me = client.get("/auth/me", headers=inspector_headers)
    inspector_id = me.json()["id"]
    manager_id = client.get("/auth/me", headers=manager_headers).json()["id"]

    own = client.post("/inspections/", json={
        "asset_id": asset_id,
        "inspector_id": inspector_id,
        "inspection_date": "2026-11-18",
        "notes": "Inspector created this",
    }, headers=inspector_headers)
    assert own.status_code == 201
    inspection_id = own.json()["id"]

    other = client.post("/inspections/", json={
        "asset_id": asset_id,
        "inspector_id": manager_id,
        "inspection_date": "2026-11-18",
    }, headers=inspector_headers)
    assert other.status_code == 403

    image = Image.new("RGB", (96, 96), color=(30, 30, 30))
    image.putpixel((10, 10), (255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    uploaded = client.post(
        f"/inspections/{inspection_id}/images",
        headers=inspector_headers,
        files={"files": ("inspector.jpg", buffer, "image/jpeg")},
    )
    assert uploaded.status_code == 201
    assert uploaded.json()[0]["inspection_id"] == inspection_id

    fetched = client.get(f"/inspections/{inspection_id}", headers=inspector_headers)
    assert fetched.status_code == 200
    assert fetched.json()["notes"] == "Inspector created this"

    db_session.expire_all()
    saved = db_session.query(InfrastructureAsset).filter(InfrastructureAsset.id == asset_id).one()
    assert saved.name == "Inspector Permission Bridge"


def test_manager_permissions_and_delete_guard(client: TestClient, db_session):
    manager = get_user_token(client, db_session, "Infrastructure Manager", "mgr_guard_m3")
    inspector = get_user_token(client, db_session, "Infrastructure Inspector", "insp_guard_m3")
    manager_headers = _auth(manager)
    inspector_headers = _auth(inspector)

    denied_users = client.get("/users/", headers=manager_headers)
    assert denied_users.status_code == 403

    created = client.post("/assets/", json={
        "asset_code": "M3-MGR-1",
        "name": "Manager Wall",
        "type": "Retaining Wall",
        "location_text": "North yard",
    }, headers=manager_headers)
    assert created.status_code == 201
    asset_id = created.json()["id"]

    updated = client.put(
        f"/assets/{asset_id}",
        json={"location_text": "South yard"},
        headers=manager_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["location_text"] == "South yard"

    reread = client.get(f"/assets/{asset_id}", headers=manager_headers)
    assert reread.status_code == 200
    assert reread.json()["location_text"] == "South yard"

    inspector_id = client.get("/auth/me", headers=inspector_headers).json()["id"]
    inspection = client.post("/inspections/", json={
        "asset_id": asset_id,
        "inspector_id": inspector_id,
        "inspection_date": "2026-11-18",
    }, headers=inspector_headers)
    assert inspection.status_code == 201

    blocked = client.delete(f"/assets/{asset_id}", headers=manager_headers)
    assert blocked.status_code == 409

    disposable = client.post("/assets/", json={
        "asset_code": "M3-MGR-DEL",
        "name": "Disposable Culvert",
        "type": "Road",
    }, headers=manager_headers)
    assert disposable.status_code == 201
    disposable_id = disposable.json()["id"]
    deleted = client.delete(f"/assets/{disposable_id}", headers=manager_headers)
    assert deleted.status_code == 204
    missing = client.get(f"/assets/{disposable_id}", headers=manager_headers)
    assert missing.status_code == 404


def _jpeg_bytes() -> bytes:
    image = Image.new("RGB", (96, 96), color=(40, 40, 40))
    image.putpixel((10, 10), (255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def _inspection_for_upload(client: TestClient, db_session, prefix: str) -> tuple[dict[str, str], int]:
    token = get_user_token(client, db_session, "Administrator", prefix)
    headers = _auth(token)
    created = client.post("/assets/", json={
        "asset_code": f"{prefix}-ASSET",
        "name": "Upload Cleanup Asset",
        "type": "Road",
    }, headers=headers)
    assert created.status_code == 201
    admin_id = client.get("/auth/me", headers=headers).json()["id"]
    inspection = client.post("/inspections/", json={
        "asset_id": created.json()["id"],
        "inspector_id": admin_id,
        "inspection_date": "2026-11-21",
    }, headers=headers)
    assert inspection.status_code == 201
    return headers, inspection.json()["id"]


def test_rejected_multi_file_upload_leaves_no_orphan(client: TestClient, db_session):
    from app.services.storage import storage

    headers, inspection_id = _inspection_for_upload(client, db_session, "m3orphan")
    before = set(Path(storage.base_dir).glob("*"))
    rejected = client.post(
        f"/inspections/{inspection_id}/images",
        headers=headers,
        files=[
            ("files", ("good.jpg", _jpeg_bytes(), "image/jpeg")),
            ("files", ("notes.txt", b"not an image", "text/plain")),
        ],
    )
    assert rejected.status_code == 400
    assert "Invalid file type" in rejected.json()["detail"]
    listed = client.get(f"/inspections/{inspection_id}/images", headers=headers)
    assert listed.status_code == 200
    assert listed.json() == []
    assert set(Path(storage.base_dir).glob("*")) == before


def test_quality_decode_failure_is_rejected(client: TestClient, db_session, monkeypatch):
    from app.services.storage import storage

    def fail_quality(*_args, **_kwargs):
        raise ValueError("Could not decode image")

    monkeypatch.setattr("app.routers.images.assess_quality", fail_quality)
    headers, inspection_id = _inspection_for_upload(client, db_session, "m3quality")
    before = set(Path(storage.base_dir).glob("*"))
    rejected = client.post(
        f"/inspections/{inspection_id}/images",
        headers=headers,
        files={"files": ("unreadable.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert rejected.status_code == 400
    assert "Could not assess image quality" in rejected.json()["detail"]
    listed = client.get(f"/inspections/{inspection_id}/images", headers=headers)
    assert listed.status_code == 200
    assert listed.json() == []
    assert set(Path(storage.base_dir).glob("*")) == before
