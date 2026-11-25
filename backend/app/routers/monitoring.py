"""Monitoring, Health, and Prometheus Metrics Endpoints."""

import os
import time
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.analysis import ModelVersion
from app.models.job import Job
from app.models.session import UserSession

router = APIRouter(tags=["Monitoring"])

# Simple in-memory metrics store for Prometheus exposition
_HTTP_REQUESTS: dict = {}
_REQUEST_DURATIONS: list = []


def record_request_metric(method: str, path: str, status_code: int, duration_sec: float):
    """Record metrics for Prometheus text export."""
    key = (method, path, status_code)
    _HTTP_REQUESTS[key] = _HTTP_REQUESTS.get(key, 0) + 1
    _REQUEST_DURATIONS.append(duration_sec)
    if len(_REQUEST_DURATIONS) > 1000:
        _REQUEST_DURATIONS.pop(0)


@router.get("/healthz")
def liveness():
    """Liveness probe: verifies process is alive."""
    return {"status": "ok", "timestamp": time.time()}


@router.get("/readyz")
def readiness(db: Session = Depends(get_db)):
    """Readiness probe: verifies database connectivity and core storage paths."""
    # Check DB
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unreachable: {str(e)}",
        )

    # Check Storage
    if not settings.upload_path.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage upload directory missing",
        )

    from app.worker import is_worker_online
    worker_status = "online" if is_worker_online() else "offline"

    return {
        "status": "ready",
        "database": "connected",
        "storage": "ready",
        "worker": worker_status,
    }


@router.get("/metrics")
def prometheus_metrics(db: Session = Depends(get_db)):
    """Expose Prometheus formatted metrics."""
    lines = [
        "# HELP http_requests_total Total number of HTTP requests processed.",
        "# TYPE http_requests_total counter",
    ]
    for (m, p, s), count in _HTTP_REQUESTS.items():
        lines.append(f'http_requests_total{{method="{m}",path="{p}",status="{s}"}} {count}')

    # Request duration summary
    avg_dur = sum(_REQUEST_DURATIONS) / len(_REQUEST_DURATIONS) if _REQUEST_DURATIONS else 0.0
    lines.extend([
        "# HELP http_request_duration_seconds Average HTTP request duration.",
        "# TYPE http_request_duration_seconds gauge",
        f"http_request_duration_seconds {avg_dur:.4f}",
    ])

    # Model inference metrics from model_versions table
    lines.extend([
        "# HELP model_inference_total Total inferences by model.",
        "# TYPE model_inference_total counter",
        "# HELP model_inference_mean_duration_ms Mean latency by model in milliseconds.",
        "# TYPE model_inference_mean_duration_ms gauge",
        "# HELP model_inference_errors_total Total errors by model.",
        "# TYPE model_inference_errors_total counter",
    ])
    try:
        models = db.query(ModelVersion).all()
        for mv in models:
            lines.append(f'model_inference_total{{model_id="{mv.model_id}"}} {mv.inferences_count or 0}')
            lines.append(f'model_inference_mean_duration_ms{{model_id="{mv.model_id}"}} {mv.mean_inference_time_ms or 0.0}')
            lines.append(f'model_inference_errors_total{{model_id="{mv.model_id}"}} {mv.error_count or 0}')
    except Exception:
        pass

    # Active sessions gauge
    try:
        active_sessions = db.query(UserSession).filter(UserSession.revoked_at == None).count()
        lines.extend([
            "# HELP active_users_gauge Currently active authenticated sessions.",
            "# TYPE active_users_gauge gauge",
            f"active_users_gauge {active_sessions}",
        ])
    except Exception:
        pass

    # Background Job queue length
    try:
        for job_status in ["pending", "running", "completed", "failed", "cancelled"]:
            cnt = db.query(Job).filter(Job.status == job_status).count()
            lines.append(f'job_queue_length_gauge{{status="{job_status}"}} {cnt}')
    except Exception:
        pass

    body = "\n".join(lines) + "\n"
    return Response(content=body, media_type="text/plain; version=0.0.4; charset=utf-8")
