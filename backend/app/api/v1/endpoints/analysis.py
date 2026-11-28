import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.models import AnalysisJob, DamageFinding, EngineerReview, ImageRecord, Inspection, User
from app.schemas.schemas import AnalysisCreate, AnalysisOut, ReviewCreate

router = APIRouter(tags=["AI Analysis & Reviews"])


@router.post("/analysis", response_model=AnalysisOut, status_code=status.HTTP_201_CREATED)
def create_analysis_job(
    payload: AnalysisCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "Engineer", "Inspector")),
):
    image = db.query(ImageRecord).filter(ImageRecord.id == payload.image_id).first()
    inspection = db.query(Inspection).filter(Inspection.id == payload.inspection_id).first()
    if not image or not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image or inspection not found")
    if image.asset_id != payload.asset_id or inspection.asset_id != payload.asset_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inconsistent asset/inspection/image")

    job = AnalysisJob(
        analysis_code=f"ANA-{uuid.uuid4().hex[:8].upper()}",
        asset_id=payload.asset_id,
        inspection_id=payload.inspection_id,
        image_id=payload.image_id,
        pipeline_type=payload.pipeline_type,
        selected_models=payload.selected_models,
        job_status="Queued",
        progress_percentage=0,
        created_by=current_user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/analysis", response_model=list[AnalysisOut])
def list_analysis_jobs(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(AnalysisJob).all()


@router.get("/analysis/{analysis_id}/status")
def get_analysis_status(analysis_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    job = db.query(AnalysisJob).filter(AnalysisJob.id == analysis_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis job not found")
    return {
        "id": job.id,
        "analysis_code": job.analysis_code,
        "job_status": job.job_status,
        "progress_percentage": job.progress_percentage,
        "is_placeholder": True,
    }


@router.post("/findings/{finding_id}/reviews", status_code=status.HTTP_201_CREATED)
def create_finding_review(
    finding_id: str,
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "Engineer")),
):
    finding = db.query(DamageFinding).filter(DamageFinding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    review = EngineerReview(
        finding_id=finding.id,
        reviewer_id=current_user.id,
        **payload.model_dump(),
    )
    finding.review_status = payload.review_decision
    db.add(review)
    db.commit()
    db.refresh(review)
    return {"id": review.id, "finding_id": finding.id, "review_decision": review.review_decision}

