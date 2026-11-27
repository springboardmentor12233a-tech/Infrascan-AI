from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional
import cv2
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import BASE_DIR, settings
from app.database import get_db
from app.deps import get_current_user
from app.models.asset import InfrastructureAsset
from app.models.damage import DamageAssessment
from app.models.image import Image as ImageModel
from app.models.inspection import Inspection
from app.models.user import User

from app.ai.damage_detection import detect_surface_defects
from app.ai.segmentation import generate_crack_mask, save_mask_visualization
from app.ai.geometry import extract_crack_geometry
from app.ai.severity import assess_damage_severity
from app.ai.explainability import generate_gradcam_heatmap
from app.services.notification_service import create_notification


router = APIRouter(tags=["AI Analysis & Damage Assessment"])


def get_image_file_path(image_record: ImageModel) -> Path:
    p = Path(image_record.file_path)
    if not p.is_absolute():
        p = BASE_DIR / p
    return p


@router.post("/images/{image_id}/analyze")
def analyze_image_damage(
    image_id: int,
    scale_mm_per_px: Optional[float] = Query(None, description="Optional calibration scale factor (mm/pixel)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run end-to-end multi-model AI damage assessment on an inspection photo:
    1. Multi-class surface damage detection (YOLO + morphological heuristics)
    2. Pixel-level crack segmentation (U-Net)
    3. Crack geometry extraction (length, avg/max width, density, orientation)
    4. Quantitative severity scoring (0-100 rating)
    5. Explainable AI (Grad-CAM saliency attention heatmap)
    """
    img_record = db.query(ImageModel).filter(ImageModel.image_id == image_id).first()
    if not img_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    file_path = get_image_file_path(img_record)
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image file missing on disk")

    img_bgr = cv2.imread(str(file_path))
    if img_bgr is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to decode image file")

    h, w = img_bgr.shape[:2]

    # 1. Pixel-level Crack Segmentation Mask
    crack_mask = generate_crack_mask(img_bgr, target_size=(w, h))

    # 2. Extract Morphological Geometry
    geometry = extract_crack_geometry(crack_mask, scale_mm_per_px=scale_mm_per_px)

    # 3. Multi-Class Surface Defect Detection
    detection_result = detect_surface_defects(img_bgr, binary_mask=crack_mask)
    primary_defect = detection_result["primary_defect"]
    confidence = detection_result["confidence"]
    detections = detection_result["detections"]

    # 4. Severity Assessment
    inspection = db.query(Inspection).filter(Inspection.inspection_id == img_record.inspection_id).first()
    asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.asset_id == inspection.asset_id).first() if inspection else None
    importance = getattr(asset, "importance_level", "medium")

    severity = assess_damage_severity(
        defect_type=primary_defect,
        max_width_px=geometry["max_width_px"],
        length_px=geometry["length_px"],
        crack_density_pct=geometry["crack_density_pct"],
        max_width_mm=geometry["max_width_mm"],
        length_mm=geometry["length_mm"],
        importance_level=importance,
    )

    # 5. Save Artifacts (Mask and Grad-CAM Heatmap)
    storage_dir = Path(settings.upload_path).parent / "analysis"
    storage_dir.mkdir(parents=True, exist_ok=True)

    mask_filename = f"mask_{image_id}.png"
    mask_disk_path = storage_dir / mask_filename
    cv2.imwrite(str(mask_disk_path), crack_mask)

    heatmap_filename = f"gradcam_{image_id}.jpg"
    heatmap_disk_path = storage_dir / heatmap_filename
    generate_gradcam_heatmap(img_bgr, crack_mask, heatmap_disk_path)

    # 6. Database Persistence
    assessment = db.query(DamageAssessment).filter(DamageAssessment.image_id == image_id).first()
    if not assessment:
        assessment = DamageAssessment(
            image_id=image_id,
            inspection_id=img_record.inspection_id,
        )
        db.add(assessment)

    assessment.defect_type = primary_defect
    assessment.confidence = confidence
    assessment.bounding_box = json.dumps(detections[0]["bounding_box"]) if detections else None
    assessment.mask_path = str(mask_disk_path)
    assessment.heatmap_path = str(heatmap_disk_path)
    assessment.crack_length_px = geometry["length_px"]
    assessment.avg_width_px = geometry["avg_width_px"]
    assessment.max_width_px = geometry["max_width_px"]
    assessment.crack_area_px = geometry["area_px"]
    assessment.crack_density_pct = geometry["crack_density_pct"]
    assessment.orientation_degrees = geometry["orientation_degrees"]
    assessment.estimated_length_mm = geometry["length_mm"]
    assessment.estimated_max_width_mm = geometry["max_width_mm"]
    assessment.scale_calibration_mm_per_px = scale_mm_per_px
    assessment.severity_category = severity["severity_category"]
    assessment.severity_score = severity["severity_score"]
    assessment.engineering_notes = severity["recommended_action"]

    db.commit()
    db.refresh(assessment)

    # Trigger critical notification if severity is severe or critical
    if severity["severity_category"] in ["severe", "critical"]:
        create_notification(
            db=db,
            title=f"Urgent: {severity['severity_category'].upper()} Damage Detected",
            message=f"Inspection #{img_record.inspection_id} detected {primary_defect.replace('_', ' ')} with severity score {severity['severity_score']}/100 on {getattr(asset, 'name', 'Asset')}.",
            severity="critical" if severity["severity_category"] == "critical" else "high",
            link=f"/inspections/{img_record.inspection_id}",
        )

    return {
        "assessment_id": assessment.assessment_id,
        "image_id": image_id,
        "inspection_id": img_record.inspection_id,
        "primary_defect": primary_defect,
        "confidence": confidence,
        "total_detections": len(detections),
        "detections": detections,
        "geometry": geometry,
        "severity": severity,
        "mask_url": f"/api/images/{image_id}/mask",
        "heatmap_url": f"/api/images/{image_id}/heatmap",
    }


@router.get("/images/{image_id}/assessment")
def get_image_assessment(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve existing damage assessment for an image."""
    assessment = db.query(DamageAssessment).filter(DamageAssessment.image_id == image_id).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found for image")

    bbox = json.loads(assessment.bounding_box) if assessment.bounding_box else None
    return {
        "assessment_id": assessment.assessment_id,
        "image_id": assessment.image_id,
        "inspection_id": assessment.inspection_id,
        "defect_type": assessment.defect_type,
        "confidence": assessment.confidence,
        "bounding_box": bbox,
        "crack_length_px": assessment.crack_length_px,
        "avg_width_px": assessment.avg_width_px,
        "max_width_px": assessment.max_width_px,
        "crack_area_px": assessment.crack_area_px,
        "crack_density_pct": assessment.crack_density_pct,
        "orientation_degrees": assessment.orientation_degrees,
        "estimated_length_mm": assessment.estimated_length_mm,
        "estimated_max_width_mm": assessment.estimated_max_width_mm,
        "severity_category": assessment.severity_category,
        "severity_score": assessment.severity_score,
        "engineering_notes": assessment.engineering_notes,
        "mask_url": f"/api/images/{image_id}/mask",
        "heatmap_url": f"/api/images/{image_id}/heatmap",
        "created_at": assessment.created_at,
    }


@router.get("/images/{image_id}/mask")
def get_image_mask(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Serve binary crack segmentation mask image."""
    assessment = db.query(DamageAssessment).filter(DamageAssessment.image_id == image_id).first()
    if not assessment or not assessment.mask_path or not Path(assessment.mask_path).is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mask not found; analyze image first")
    return FileResponse(assessment.mask_path, media_type="image/png")


@router.get("/images/{image_id}/heatmap")
def get_image_heatmap(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Serve Explainable AI Grad-CAM saliency attention heatmap."""
    assessment = db.query(DamageAssessment).filter(DamageAssessment.image_id == image_id).first()
    if not assessment or not assessment.heatmap_path or not Path(assessment.heatmap_path).is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Heatmap not found; analyze image first")
    return FileResponse(assessment.heatmap_path, media_type="image/jpeg")


@router.get("/inspections/{inspection_id}/assessment-summary")
def get_inspection_assessment_summary(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aggregate all damage findings and compute overall inspection health score."""
    assessments = db.query(DamageAssessment).filter(DamageAssessment.inspection_id == inspection_id).all()
    if not assessments:
        return {
            "inspection_id": inspection_id,
            "total_assessments": 0,
            "overall_severity": "no_damage",
            "overall_score": 0.0,
            "findings": [],
        }

    scores = [a.severity_score for a in assessments]
    max_score = max(scores)
    avg_score = round(sum(scores) / len(scores), 1)

    top_finding = max(assessments, key=lambda a: a.severity_score)
    top_sev = top_finding.severity_category

    return {
        "inspection_id": inspection_id,
        "total_assessments": len(assessments),
        "max_severity_score": max_score,
        "avg_severity_score": avg_score,
        "overall_severity": top_sev,
        "dominant_defect": top_finding.defect_type,
        "recommended_action": top_finding.engineering_notes,
        "findings": [
            {
                "assessment_id": a.assessment_id,
                "image_id": a.image_id,
                "defect_type": a.defect_type,
                "severity_category": a.severity_category,
                "severity_score": a.severity_score,
                "crack_length_px": a.crack_length_px,
                "max_width_px": a.max_width_px,
            }
            for a in assessments
        ],
    }
