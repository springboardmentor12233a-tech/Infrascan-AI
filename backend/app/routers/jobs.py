"""Router for Asynchronous Background Jobs."""

import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobCreate, JobListResponse, JobResponse
from app.services.audit import create_audit_log
from app.services.event_service import publish

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _format_job(job: Job) -> Dict[str, Any]:
    return {
        "id": job.id,
        "job_type": job.job_type,
        "status": job.status,
        "progress": job.progress,
        "payload": json.loads(job.payload_json) if job.payload_json else {},
        "result": json.loads(job.result_json) if job.result_json else None,
        "error_message": job.error_message,
        "retries": job.retries,
        "max_retries": job.max_retries,
        "user_id": job.user_id,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
    }


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def enqueue_job(
    req: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enqueue a new asynchronous background job."""
    valid_types = {"analysis_run", "report_generation", "batch_import"}
    if req.job_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid job_type '{req.job_type}'. Must be one of: {sorted(list(valid_types))}",
        )

    job = Job(
        job_type=req.job_type,
        payload_json=json.dumps(req.payload),
        status="pending",
        progress=0,
        max_retries=req.max_retries,
        user_id=current_user.user_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    create_audit_log(
        db=db,
        user_id=current_user.user_id,
        action="job_enqueued",
        entity_type="job",
        entity_id=str(job.id),
    )

    return _format_job(job)


@router.get("", response_model=JobListResponse)
def list_jobs(
    status_filter: Optional[str] = Query(None, alias="status"),
    job_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List jobs with pagination and filters."""
    query = db.query(Job)
    if status_filter:
        query = query.filter(Job.status == status_filter)
    if job_type:
        query = query.filter(Job.job_type == job_type)

    # Inspectors only see their own jobs; engineers/managers/admins see all
    if current_user.role == "inspector":
        query = query.filter(Job.user_id == current_user.user_id)

    total = query.count()
    jobs = (
        query.order_by(Job.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "jobs": [_format_job(j) for j in jobs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get single job status and progress."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job #{job_id} not found.")

    if current_user.role == "inspector" and job.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this job.")

    return _format_job(job)


@router.post("/{job_id}/cancel", response_model=JobResponse)
def cancel_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a pending or running job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job #{job_id} not found.")

    if current_user.role == "inspector" and job.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this job.")

    if job.status in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel job with status '{job.status}'.")

    job.status = "cancelled"
    db.commit()
    db.refresh(job)

    create_audit_log(
        db=db,
        user_id=current_user.user_id,
        action="job_cancelled",
        entity_type="job",
        entity_id=str(job.id),
    )

    return _format_job(job)


@router.post("/{job_id}/retry", response_model=JobResponse)
def retry_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retry a failed or cancelled job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job #{job_id} not found.")

    if current_user.role == "inspector" and job.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to retry this job.")

    if job.status not in ("failed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot retry job with status '{job.status}'.")

    job.status = "pending"
    job.progress = 0
    job.error_message = None
    job.retries = 0
    db.commit()
    db.refresh(job)

    publish(
        db=db,
        event_type="job.queued",
        entity_type="job",
        entity_id=job.id,
        audience={"roles": ["admin", "manager"], "user_ids": [job.user_id]},
        payload={"job_id": job.id, "status": "pending"},
    )

    create_audit_log(
        db=db,
        user_id=current_user.user_id,
        action="job_retried",
        entity_type="job",
        entity_id=str(job.id),
    )

    return _format_job(job)


@router.get("/worker/status")
def get_worker_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get status of background worker and queue counts."""
    from app.worker import is_worker_online
    from sqlalchemy import func
    counts = dict(
        db.query(Job.status, func.count(Job.id))
        .group_by(Job.status)
        .all()
    )
    return {
        "worker_status": "online" if is_worker_online() else "offline",
        "pending": counts.get("pending", 0),
        "running": counts.get("running", 0),
        "failed": counts.get("failed", 0),
        "completed": counts.get("completed", 0),
        "cancelled": counts.get("cancelled", 0),
    }
