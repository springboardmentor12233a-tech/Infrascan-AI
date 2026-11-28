import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.ml.engine import ml_engine
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


@router.get("/analysis/model-status")
def get_model_status(_: User = Depends(get_current_user)):
    return {
        "model_name": "YOLOv8-RDD2022",
        "weights_path": str(ml_engine.weights_path),
        "weights_available": ml_engine.weights_available,
        "status": "trained_and_available" if ml_engine.weights_available else "weights_unavailable",
    }


@router.post("/analysis/infer/{image_id}")
def run_image_inference(
    image_id: str,
    px_per_mm: float | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "Engineer", "Inspector")),
):
    image = db.query(ImageRecord).filter(ImageRecord.id == image_id).first()
    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    annotated_path = Path(settings.STORAGE_DIR) / "annotated" / f"{image.id}_annotated.jpg"
    result = ml_engine.run_inference(
        image_path=image.storage_path,
        annotated_output_path=str(annotated_path),
        px_per_mm=px_per_mm,
    )

    image.image_quality_status = result["quality"]["quality_status"]
    db.commit()

    return {
        "image_id": image.id,
        "filename": image.original_filename,
        "annotated_url": f"/api/v1/analysis/annotated/{image.id}" if result["annotated_image_path"] else None,
        **result,
    }


@router.get("/analysis/annotated/{image_id}")
def get_annotated_image(image_id: str, _: User = Depends(get_current_user)):
    annotated_path = Path(settings.STORAGE_DIR) / "annotated" / f"{image_id}_annotated.jpg"
    if not annotated_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotated image not found")
    return FileResponse(annotated_path)


@router.post("/analysis/infer-upload")
async def infer_uploaded_image(
    file: UploadFile = File(...),
    px_per_mm: float | None = None,
):
    """
    Direct image-to-prediction endpoint for uploaded inspection images.
    Runs real OpenCV quality assessment and YOLOv8 inference if weights exist;
    explicitly returns weights_unavailable if trained weights are missing.
    """
    temp_dir = Path(settings.STORAGE_DIR) / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_id = uuid.uuid4().hex[:12]
    ext = Path(file.filename or "upload.jpg").suffix or ".jpg"
    temp_path = temp_dir / f"{temp_id}{ext}"
    annotated_path = Path(settings.STORAGE_DIR) / "annotated" / f"{temp_id}_annotated.jpg"

    content = await file.read()
    temp_path.write_bytes(content)

    try:
        result = ml_engine.run_inference(
            image_path=str(temp_path),
            annotated_output_path=str(annotated_path),
            px_per_mm=px_per_mm,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return {
        "image_id": temp_id,
        "filename": file.filename,
        "annotated_url": f"/api/v1/analysis/annotated/{temp_id}" if result["annotated_image_path"] else None,
        **result,
    }

