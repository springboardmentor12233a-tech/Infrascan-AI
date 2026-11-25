"""Dashboard Attention Feeds Router.

Provides role-specific 'Needs your attention' actionable data for:
- inspector: inspections awaiting upload, quality warnings, failed analyses
- civil_engineer: results to review, priorities to confirm, tasks to verify
- maintenance_engineer: open and overdue maintenance tasks
- manager: overdue inspections, high-priority findings without a maintenance task
- admin: failed jobs, worker offline, system/security alerts
"""

from datetime import datetime, date, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.deps import get_current_user
from app.models.analysis import AnalysisRun, ImageScale
from app.models.image import Image as ImageModel
from app.models.inspection import Inspection
from app.models.job import Job
from app.models.maintenance import MaintenancePriority, MaintenanceTask
from app.models.severity import SeverityAssessment
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

DISCLAIMER = "AI result for engineer review, not a final structural safety verdict."


@router.get("/attention")
def get_attention_feed(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve actionable 'Needs your attention' feed for the active user's role."""
    now = datetime.now(timezone.utc)
    today = date.today()
    role = current_user.role
    items: List[Dict[str, Any]] = []

    if role == "inspector":
        # 1. Inspections waiting for upload
        waiting_inspections = (
            db.query(Inspection)
            .filter(
                Inspection.inspector_id == current_user.user_id,
                Inspection.status.in_(["assigned", "in_progress"]),
            )
            .order_by(Inspection.inspection_date.asc())
            .limit(10)
            .all()
        )
        for insp in waiting_inspections:
            asset_name = insp.asset.name if insp.asset else f"Asset #{insp.asset_id}"
            items.append({
                "id": f"insp_{insp.inspection_id}",
                "category": "waiting_upload",
                "title": f"Inspection #{insp.inspection_id} Awaiting Upload",
                "description": f"Inspection for '{asset_name}' is {insp.status}. Upload inspection photos.",
                "severity": "medium",
                "link": f"/inspections/{insp.inspection_id}",
                "created_at": insp.created_at.isoformat() if insp.created_at else None,
            })

        # 2. Quality warnings on uploaded images
        warn_images = (
            db.query(ImageModel)
            .filter(
                ImageModel.uploaded_by == current_user.user_id,
                ImageModel.quality_status == "warning",
            )
            .order_by(ImageModel.image_id.desc())
            .limit(10)
            .all()
        )
        for img in warn_images:
            items.append({
                "id": f"img_warn_{img.image_id}",
                "category": "quality_warning",
                "title": f"Quality Warning on Image #{img.image_id}",
                "description": f"File '{img.original_filename}' has blur/brightness issues. Consider retaking.",
                "severity": "medium",
                "link": f"/inspections/{img.inspection_id}",
                "created_at": img.created_at.isoformat() if img.created_at else None,
            })

        # 3. Failed analyses
        failed_runs = (
            db.query(AnalysisRun)
            .join(ImageModel, AnalysisRun.image_id == ImageModel.image_id)
            .filter(
                ImageModel.uploaded_by == current_user.user_id,
                AnalysisRun.status == "failed",
            )
            .order_by(AnalysisRun.run_id.desc())
            .limit(10)
            .all()
        )
        for fr in failed_runs:
            items.append({
                "id": f"run_fail_{fr.run_id}",
                "category": "failed_analysis",
                "title": f"Analysis Run #{fr.run_id} Failed",
                "description": fr.error_message or "AI model inference failed. Qualified engineering review required.",
                "severity": "high",
                "link": f"/inspections/{fr.image.inspection_id}" if fr.image else "/inspections",
                "created_at": fr.started_at.isoformat() if fr.started_at else None,
            })

    elif role == "civil_engineer":
        # 1. Results to review (pending severity assessments)
        pending_sevs = (
            db.query(SeverityAssessment)
            .filter(
                SeverityAssessment.review_status == "pending",
                SeverityAssessment.is_superseded == False,
            )
            .order_by(SeverityAssessment.assessment_id.desc())
            .limit(15)
            .all()
        )
        for s in pending_sevs:
            sev_level = s.severity_level or "unknown"
            is_crit = sev_level in ("severe", "critical")
            items.append({
                "id": f"sev_{s.assessment_id}",
                "category": "results_to_review",
                "title": f"Severity Review: Image #{s.image_id} ({sev_level.upper()})",
                "description": f"Advisory severity '{sev_level}' (score {s.score:.1f}). Qualified engineering review required.",
                "severity": "critical" if is_crit else "medium",
                "link": f"/inspections/{s.image.inspection_id}" if s.image else "/inspections",
                "created_at": s.created_at.isoformat() if s.created_at else None,
            })

        # 2. Priorities to confirm
        provisional_priorities = (
            db.query(MaintenancePriority)
            .filter(
                (MaintenancePriority.provisional == True) | (MaintenancePriority.status == "suggested")
            )
            .order_by(MaintenancePriority.priority_id.desc())
            .limit(10)
            .all()
        )
        for p in provisional_priorities:
            items.append({
                "id": f"prio_{p.priority_id}",
                "category": "priorities_to_confirm",
                "title": f"Confirm Priority: Asset #{p.asset_id} ({p.suggested_priority})",
                "description": f"Suggested priority '{p.suggested_priority}'. Needs civil engineer confirmation or override.",
                "severity": "high" if p.suggested_priority in ("P1", "P2") else "medium",
                "link": f"/maintenance",
                "created_at": p.created_at.isoformat() if p.created_at else None,
            })

        # 3. Tasks to verify
        tasks_to_verify = (
            db.query(MaintenanceTask)
            .filter(MaintenanceTask.status == "completed")
            .order_by(MaintenanceTask.task_id.desc())
            .limit(10)
            .all()
        )
        for t in tasks_to_verify:
            items.append({
                "id": f"verify_task_{t.task_id}",
                "category": "tasks_to_verify",
                "title": f"Verify Task #{t.task_id}: {t.title}",
                "description": f"Completed by maintenance engineer with notes: '{t.resolution_notes or 'None'}'. Verify completion.",
                "severity": "medium",
                "link": f"/maintenance",
                "created_at": t.completed_at.isoformat() if t.completed_at else None,
            })

    elif role == "maintenance_engineer":
        # 1. Assigned open tasks
        assigned_tasks = (
            db.query(MaintenanceTask)
            .filter(
                MaintenanceTask.assigned_to == current_user.user_id,
                MaintenanceTask.status.in_(["assigned", "open", "in_progress"]),
            )
            .order_by(MaintenanceTask.task_id.desc())
            .limit(15)
            .all()
        )
        for t in assigned_tasks:
            is_overdue = t.due_date and t.due_date.date() < today
            items.append({
                "id": f"task_{t.task_id}",
                "category": "overdue_tasks" if is_overdue else "open_tasks",
                "title": f"Task #{t.task_id}: {t.title} [{t.priority}]",
                "description": f"Status: {t.status}. Due: {t.due_date.strftime('%Y-%m-%d') if t.due_date else 'No due date'}" + (" (OVERDUE)" if is_overdue else ""),
                "severity": "critical" if is_overdue or t.priority == "P1" else "high" if t.priority == "P2" else "medium",
                "link": "/maintenance",
                "created_at": t.created_at.isoformat() if t.created_at else None,
            })

    elif role == "manager":
        # 1. Overdue inspections
        overdue_insps = (
            db.query(Inspection)
            .filter(
                Inspection.status.in_(["assigned", "in_progress"]),
                Inspection.inspection_date < today,
            )
            .order_by(Inspection.inspection_date.asc())
            .limit(10)
            .all()
        )
        for oi in overdue_insps:
            asset_name = oi.asset.name if oi.asset else f"Asset #{oi.asset_id}"
            items.append({
                "id": f"overdue_insp_{oi.inspection_id}",
                "category": "overdue_inspections",
                "title": f"Overdue Inspection #{oi.inspection_id}",
                "description": f"Scheduled for {oi.inspection_date.strftime('%Y-%m-%d')} on '{asset_name}'. Status: {oi.status}.",
                "severity": "high",
                "link": f"/inspections/{oi.inspection_id}",
                "created_at": oi.created_at.isoformat() if oi.created_at else None,
            })

        # 2. High priority findings without maintenance tasks
        # Unassigned high severity assessments
        high_sevs = (
            db.query(SeverityAssessment)
            .filter(
                SeverityAssessment.severity_level.in_(["severe", "critical"]),
                SeverityAssessment.is_superseded == False,
            )
            .order_by(SeverityAssessment.assessment_id.desc())
            .limit(10)
            .all()
        )
        # Check which have existing tasks
        existing_task_asset_ids = set(r[0] for r in db.query(MaintenanceTask.asset_id).all())
        for hs in high_sevs:
            asset_id = hs.image.inspection.asset_id if (hs.image and hs.image.inspection) else None
            if asset_id and asset_id not in existing_task_asset_ids:
                items.append({
                    "id": f"unassigned_high_{hs.assessment_id}",
                    "category": "high_priority_unassigned",
                    "title": f"High Priority Finding: Asset #{asset_id} ({hs.severity_level.upper()})",
                    "description": f"Severe/critical damage identified by AI without open maintenance task. Qualified engineering review required.",
                    "severity": "critical",
                    "link": f"/maintenance",
                    "created_at": hs.created_at.isoformat() if hs.created_at else None,
                })

    elif role == "admin":
        # 1. Failed jobs
        failed_jobs = (
            db.query(Job)
            .filter(Job.status == "failed")
            .order_by(Job.id.desc())
            .limit(10)
            .all()
        )
        for fj in failed_jobs:
            items.append({
                "id": f"job_{fj.id}",
                "category": "failed_jobs",
                "title": f"Failed Job #{fj.id} ({fj.job_type})",
                "description": fj.error_message or "Job execution failed.",
                "severity": "high",
                "link": "/jobs",
                "created_at": fj.completed_at.isoformat() if fj.completed_at else None,
            })

    return {
        "role": role,
        "items": items,
        "count": len(items),
        "disclaimer": DISCLAIMER,
    }
