import io
import json
import os
from datetime import datetime, timezone
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["TESTING"] = "1"

from app.database import Base, get_db
from app.main import app
from app.models.analysis import ModelVersion
from app.models.dataset import DatasetVersion, ModelEvent
from app.models.job import Job
from app.models.user import User
from app.services import model_registry
from app.services.classifier_service import SCREENING_DISCLAIMER
from app.services.security import create_access_token, hash_password
from app.worker import execute_job

# Test SQLite in-memory DB
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


def make_user(db_session, email="admin@example.com", role="admin"):
    user = User(
        email=email,
        full_name="Admin User",
        password_hash=hash_password("SecurePass123!"),
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def make_auth_headers(user):
    token = create_access_token(data={"sub": user.email, "role": user.role, "type": "access"})
    return {"Authorization": f"Bearer {token}"}


def test_model_registry_seed_and_list(client, db_session):
    """Test default models and datasets are seeded and retrievable via API."""
    user = make_user(db_session, role="admin")
    headers = make_auth_headers(user)

    resp = client.get("/models/registry", headers=headers)
    assert resp.status_code == 200
    models = resp.json()
    assert len(models) >= 4

    model_ids = [m["model_id"] for m in models]
    assert "yolov8s_rdd2022" in model_ids
    assert "unetplusplus_crack500" in model_ids
    assert "resnet50_sdnet2018" in model_ids

    # Datasets endpoint
    ds_resp = client.get("/models/datasets", headers=headers)
    assert ds_resp.status_code == 200
    datasets = ds_resp.json()
    assert len(datasets) >= 4
    ds_names = [d["name"] for d in datasets]
    assert "SDNET2018" in ds_names
    assert "Crack500" in ds_names


def test_model_activation_and_rollback(client, db_session, monkeypatch):
    """Test model smoke test, activation, rollback, and event audit logging."""
    user = make_user(db_session, role="admin")
    headers = make_auth_headers(user)

    model_registry.seed_default_models(db_session)

    # Register an alternative segmentation model
    alt_model = ModelVersion(
        model_id="unetplusplus_v2",
        model_name="U-Net++ ResNet-34 v2",
        task="segmentation",
        version="2.0",
        weights_path="dummy_path.pth",
        threshold=0.45,
        is_active=False,
    )
    db_session.add(alt_model)
    db_session.commit()

    # 1. Activation failure when smoke test fails
    def mock_smoke_test_fail(weights_path, task):
        raise RuntimeError("Weights file corrupted or invalid architecture.")

    monkeypatch.setattr(model_registry, "smoke_test_model", mock_smoke_test_fail)

    act_resp = client.post("/models/unetplusplus_v2/activate", headers=headers)
    assert act_resp.status_code == 422
    assert "Activation rejected" in act_resp.json()["detail"]

    # Verify model is still inactive and previous active is still active
    db_session.refresh(alt_model)
    assert alt_model.is_active is False
    orig_model = model_registry.get_model_by_id(db_session, "unetplusplus_crack500")
    assert orig_model.is_active is True

    # 2. Activation success when smoke test succeeds
    def mock_smoke_test_pass(weights_path, task):
        return True

    monkeypatch.setattr(model_registry, "smoke_test_model", mock_smoke_test_pass)

    act_resp2 = client.post("/models/unetplusplus_v2/activate", headers=headers)
    assert act_resp2.status_code == 200
    assert act_resp2.json()["is_active"] is True

    db_session.refresh(alt_model)
    db_session.refresh(orig_model)
    assert alt_model.is_active is True
    assert orig_model.is_active is False

    # Check ModelEvent logged
    events_resp = client.get("/models/unetplusplus_v2/events", headers=headers)
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert len(events) >= 1
    assert events[0]["event_type"] == "activated"

    # 3. Rollback
    rb_resp = client.post("/models/unetplusplus_v2/rollback", headers=headers)
    assert rb_resp.status_code == 200
    assert rb_resp.json()["is_active"] is False

    db_session.refresh(alt_model)
    db_session.refresh(orig_model)
    assert alt_model.is_active is False
    assert orig_model.is_active is True


def test_real_use_inference_metrics_tracking(db_session):
    """Test real-use inference metrics (latency, running mean, errors) updating."""
    model_registry.seed_default_models(db_session)
    model_id = "yolov8s_rdd2022"

    # Simulate 3 successful inferences
    model_registry.record_inference_metrics(db_session, model_id, latency_ms=100.0, success=True)
    model_registry.record_inference_metrics(db_session, model_id, latency_ms=200.0, success=True)
    model_registry.record_inference_metrics(db_session, model_id, latency_ms=300.0, success=True)

    m = model_registry.get_model_by_id(db_session, model_id)
    assert m.inferences_count == 3
    assert m.mean_inference_time_ms == 200.0
    assert m.last_inference_at is not None
    assert m.error_count == 0

    # Simulate 1 error
    model_registry.record_inference_metrics(db_session, model_id, latency_ms=0.0, success=False)
    db_session.refresh(m)
    assert m.inferences_count == 3
    assert m.error_count == 1


def test_crop_classification_dimensions_guard(client, db_session):
    """Test crop classification rejects images larger than 600px with HTTP 422."""
    user = make_user(db_session, role="civil_engineer")
    headers = make_auth_headers(user)

    # Create oversized 800x800 image
    oversized = np.zeros((800, 800, 3), dtype=np.uint8)
    _, img_bytes = cv2.imencode(".jpg", oversized)

    files = {"file": ("large_crop.jpg", io.BytesIO(img_bytes.tobytes()), "image/jpeg")}
    resp = client.post("/classify-crop", files=files, headers=headers)
    assert resp.status_code == 422
    assert "exceeds maximum 600px limit" in resp.json()["detail"]


def test_crop_classification_success_and_disclaimer(client, db_session, monkeypatch):
    """Test crop classification succeeds and returns mandatory screening disclaimer."""
    user = make_user(db_session, role="civil_engineer")
    headers = make_auth_headers(user)

    # Create valid 200x200 crop image
    valid_crop = np.full((200, 200, 3), 128, dtype=np.uint8)
    _, img_bytes = cv2.imencode(".jpg", valid_crop)

    # Mock classifier output
    import torch
    class DummyClassifier:
        def __call__(self, x):
            return torch.tensor([[1.5]])  # sigmoid(1.5) ~= 0.8176
        def eval(self):
            return self

    monkeypatch.setattr("app.services.classifier_service.load_classifier", lambda: DummyClassifier())

    files = {"file": ("valid_crop.jpg", io.BytesIO(img_bytes.tobytes()), "image/jpeg")}
    resp = client.post("/classify-crop", files=files, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["is_cracked"] is True
    assert data["label"] == "cracked"
    assert data["crack_probability"] > 0.8
    assert data["crop_dimensions"]["width"] == 200
    assert data["crop_dimensions"]["height"] == 200
    assert data["screening_disclaimer"] == SCREENING_DISCLAIMER
    assert "AI result for engineer review, not a final structural safety verdict." in data["screening_disclaimer"]


def test_job_queue_and_worker_execution(client, db_session):
    """Test job enqueuing, listing, worker processing, retries, and cancellation."""
    user = make_user(db_session, role="inspector")
    headers = make_auth_headers(user)

    # 1. Enqueue job
    job_payload = {
        "job_type": "batch_import",
        "payload": {"items": ["item1.jpg", "item2.jpg"]},
        "max_retries": 2,
    }
    resp = client.post("/jobs", json=job_payload, headers=headers)
    assert resp.status_code == 201
    job_data = resp.json()
    job_id = job_data["id"]
    assert job_data["status"] == "pending"
    assert job_data["progress"] == 0

    # 2. List jobs
    list_resp = client.get("/jobs", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    # 3. Worker execution
    success = execute_job(job_id=job_id, db=db_session)
    assert success is True

    # 4. Verify completed state
    get_resp = client.get(f"/jobs/{job_id}", headers=headers)
    assert get_resp.status_code == 200
    completed_data = get_resp.json()
    assert completed_data["status"] == "completed"
    assert completed_data["progress"] == 100
    assert completed_data["result"]["imported_count"] == 2

    # 5. Test Cancellation on a second job
    resp2 = client.post("/jobs", json=job_payload, headers=headers)
    job2_id = resp2.json()["id"]

    cancel_resp = client.post(f"/jobs/{job2_id}/cancel", headers=headers)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    # Cannot cancel already completed or cancelled job
    cancel_again = client.post(f"/jobs/{job2_id}/cancel", headers=headers)
    assert cancel_again.status_code == 400
