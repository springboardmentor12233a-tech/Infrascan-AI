"""API router for damage severity assessment."""

import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.analysis import AnalysisRun
from app.models.image import Image as ImageModel
from app.models.inspection import Inspection
from app.models.severity import InspectionSeverity, SeverityAssessment
from app.models.user import User
from app.schemas.severity import (
    FactorDetail,
    InspectionSeverityDetailResponse,
    InspectionSeverityResponse,
    ReviewActionRequest,
    SeverityAssessmentResponse,
    SeverityRulesResponse,
)
from app.services.audit import create_audit_log
from app.services.event_service import publish
from app.services.severity_service import (
    SEVERITY_ORDER,
    SEVERITY_RANK,
    assess_and_save_run,
    load_severity_rules,
    update_inspection_severity,
)

router = APIRouter(tags=["Severity"])


def _format_assessment_response(assessment: SeverityAssessment) -> SeverityAssessmentResponse:
    """Helper to convert SeverityAssessment model into detailed Pydantic schema."""
    factors = []
    if assessment.factors_json:
        try:
            factors_data = json.loads(assessment.factors_json)
            factors = [FactorDetail(**f) for f in factors_data]
        except Exception:
            factors = []

    warnings = []
    if assessment.warnings_json:
        try:
            warnings = json.loads(assessment.warnings_json)
        except Exception:
            warnings = []

    low_conf = False
    for f in factors:
        if f.factor == "damage_type" and isinstance(f.input_value, dict):
            conf = f.input_value.get("confidence", 1.0)
            if 0.0 < conf < 0.40:
                low_conf = True

    return SeverityAssessmentResponse(
        assessment_id=assessment.assessment_id,
        run_id=assessment.run_id,
        image_id=assessment.image_id,
        severity_level=assessment.severity_level,
        score=assessment.score,
        priority_suggestion=assessment.priority_suggestion,
        factors_json=assessment.factors_json,
        warnings_json=assessment.warnings_json,
        rules_version=assessment.rules_version,
        rules_sha256=assessment.rules_sha256,
        review_status=assessment.review_status,
        reviewed_by=assessment.reviewed_by,
        reviewed_at=assessment.reviewed_at,
        final_severity=assessment.final_severity,
        final_priority=assessment.final_priority,
        review_comment=assessment.review_comment,
        is_superseded=assessment.is_superseded,
        created_at=assessment.created_at,
        factors=factors,
        warnings=warnings,
        needs_review=(assessment.review_status == "pending"),
        low_confidence_review=low_conf,
    )


# 1. GET /images/{id}/severity - same visibility rules as the image
@router.get("/images/{id}/severity", response_model=SeverityAssessmentResponse)
def get_image_severity(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve advisory severity assessment for an image."""
    image = db.query(ImageModel).filter(ImageModel.image_id == id).first()
    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    if current_user.role == "inspector":
        if image.inspection and image.inspection.inspector_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this image severity.",
            )

    assessment = (
        db.query(SeverityAssessment)
        .filter(SeverityAssessment.image_id == id, SeverityAssessment.is_superseded == False)
        .order_by(SeverityAssessment.assessment_id.desc())
        .first()
    )

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No severity assessment found for this image.",
        )

    return _format_assessment_response(assessment)


# 2. GET /inspections/{id}/severity - aggregate plus the list
@router.get("/inspections/{id}/severity", response_model=InspectionSeverityDetailResponse)
def get_inspection_severity(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve aggregate severity for an inspection and all image assessments."""
    inspection = db.query(Inspection).filter(Inspection.inspection_id == id).first()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    if current_user.role == "inspector" and inspection.inspector_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this inspection severity.",
        )

    images = db.query(ImageModel).filter(ImageModel.inspection_id == id).all()
    image_ids = [img.image_id for img in images]

    assessments = (
        db.query(SeverityAssessment)
        .filter(
            SeverityAssessment.image_id.in_(image_ids),
            SeverityAssessment.is_superseded == False,
        )
        .order_by(SeverityAssessment.assessment_id.desc())
        .all()
    ) if image_ids else []

    # Map newest per image
    unique_assessments: dict = {}
    for a in assessments:
        if a.image_id not in unique_assessments:
            unique_assessments[a.image_id] = a

    assessment_list = [_format_assessment_response(a) for a in unique_assessments.values()]

    # Get or update aggregate record
    agg = (
        db.query(InspectionSeverity)
        .filter(InspectionSeverity.inspection_id == id)
        .first()
    )

    if not agg and image_ids:
        agg = update_inspection_severity(id, db)

    worst_sev = agg.worst_severity if agg else "none"
    worst_sc = agg.worst_score if agg else 0.0
    images_assessed = agg.images_assessed if agg else len(assessment_list)
    images_pending = agg.images_pending_review if agg else sum(1 for a in assessment_list if a.review_status == "pending")
    summary = json.loads(agg.summary_json) if (agg and agg.summary_json) else {
        "counts": {k: 0 for k in SEVERITY_ORDER},
        "worst_severity": worst_sev,
        "worst_score": worst_sc,
        "images_assessed": images_assessed,
        "images_pending_review": images_pending,
        "aggregation_rule": "The inspection severity is the WORST image severity (final_severity where reviewed), with counts per level.",
    }

    return InspectionSeverityDetailResponse(
        inspection_id=id,
        worst_severity=worst_sev,
        worst_score=worst_sc,
        images_assessed=images_assessed,
        images_pending_review=images_pending,
        summary=summary,
        assessments=assessment_list,
    )


# 3. POST /images/{id}/severity/recompute - admin, civil_engineer only
@router.post("/images/{id}/severity/recompute", response_model=SeverityAssessmentResponse)
def recompute_image_severity(
    id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Recompute severity using saved results and current rules. Marks old row superseded."""
    if current_user.role not in ["admin", "civil_engineer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin and civil engineers can recompute severity assessments.",
        )

    image = db.query(ImageModel).filter(ImageModel.image_id == id).first()
    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    run = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.image_id == id, AnalysisRun.status == "done")
        .order_by(AnalysisRun.run_id.desc())
        .first()
    )
    if not run:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No completed analysis run found for this image to recompute severity.",
        )

    # Recompute and persist (automatically marks previous active row as superseded)
    new_assessment = assess_and_save_run(run_id=run.run_id, db=db)
    if not new_assessment:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to recompute severity assessment.",
        )

    create_audit_log(
        db=db,
        action="severity_recomputed",
        user_id=current_user.user_id,
        entity_type="severity_assessment",
        entity_id=str(new_assessment.assessment_id),
        ip_address=request.client.host if request.client else None,
    )

    return _format_assessment_response(new_assessment)


# 4. PUT /severity/{assessment_id}/review - civil_engineer, admin only
@router.put("/severity/{assessment_id}/review", response_model=SeverityAssessmentResponse)
def review_severity_assessment(
    assessment_id: int,
    body: ReviewActionRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Confirm or correct an advisory severity assessment. Inspectors get 403."""
    if current_user.role not in ["admin", "civil_engineer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only civil engineers and administrators can review or correct severity assessments.",
        )

    assessment = (
        db.query(SeverityAssessment)
        .filter(SeverityAssessment.assessment_id == assessment_id)
        .first()
    )
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Severity assessment not found.",
        )

    action_lower = body.action.lower().strip()
    if action_lower not in ["confirm", "correct"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Action must be either 'confirm' or 'correct'.",
        )

    if action_lower == "correct":
        if not body.final_severity or body.final_severity.lower() not in SEVERITY_RANK:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"final_severity is required for correction and must be one of {SEVERITY_ORDER}.",
            )
        if not body.comment or not body.comment.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A non-empty review comment is required when correcting severity.",
            )

    old_status = assessment.review_status
    old_severity = assessment.final_severity or assessment.severity_level

    assessment.reviewed_by = current_user.user_id
    assessment.reviewed_at = datetime.now(timezone.utc)
    assessment.review_comment = body.comment.strip() if body.comment else None

    if action_lower == "confirm":
        assessment.review_status = "confirmed"
        assessment.final_severity = assessment.severity_level
        assessment.final_priority = assessment.priority_suggestion
    else:
        assessment.review_status = "corrected"
        assessment.final_severity = body.final_severity.lower()
        if body.final_priority:
            assessment.final_priority = body.final_priority
        else:
            assessment.final_priority = assessment.priority_suggestion

    publish(
        db=db,
        event_type="severity.reviewed",
        entity_type="severity_assessment",
        entity_id=assessment.assessment_id,
        audience={"all": True},
        payload={
            "assessment_id": assessment.assessment_id,
            "review_status": assessment.review_status,
            "final_severity": assessment.final_severity,
            "final_priority": assessment.final_priority,
            "is_confirmed": True,
        },
    )
    publish(
        db=db,
        event_type="severity.confirmed",
        entity_type="severity_assessment",
        entity_id=assessment.assessment_id,
        audience={"all": True},
        payload={
            "assessment_id": assessment.assessment_id,
            "review_status": assessment.review_status,
            "final_severity": assessment.final_severity,
            "final_priority": assessment.final_priority,
            "is_confirmed": True,
        },
    )
    db.commit()
    db.refresh(assessment)

    # Record audit log with complete before/after history
    audit_action = (
        f"severity_{action_lower}: assessment_id={assessment_id}, "
        f"old_status='{old_status}', new_status='{assessment.review_status}', "
        f"old_severity='{old_severity}', new_severity='{assessment.final_severity}', "
        f"comment='{assessment.review_comment}'"
    )
    create_audit_log(
        db=db,
        action=audit_action,
        user_id=current_user.user_id,
        entity_type="severity_assessment",
        entity_id=str(assessment.assessment_id),
        ip_address=request.client.host if request.client else None,
    )

    # Update inspection aggregate severity
    if assessment.image and assessment.image.inspection_id:
        update_inspection_severity(assessment.image.inspection_id, db)

    return _format_assessment_response(assessment)


# 5. GET /severity/rules - any logged-in user (read-only)
@router.get("/severity/rules", response_model=SeverityRulesResponse)
def get_severity_rules(
    current_user: User = Depends(get_current_user),
):
    """Retrieve the current active severity assessment rules with version and SHA-256 hash."""
    try:
        rules, rules_sha256 = load_severity_rules()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load severity rules: {exc}",
        )

    return SeverityRulesResponse(
        rules_version=rules.get("rules_version", "1.0.0"),
        status=rules.get("status", "engineer-defined placeholders, not validated against an engineering standard"),
        rules_sha256=rules_sha256,
        rules=rules,
    )

