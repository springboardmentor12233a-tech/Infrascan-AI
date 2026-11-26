import os
import json
import shutil
import traceback
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Asset, Inspection, InspectionResult, User
from auth import get_current_user
from services.image_quality import assess_image_quality
from services.classifier import run_crack_classification
from services.detector import run_crack_detection
from services.segmentor import run_crack_segmentation
from services.geometry import extract_crack_geometry
from services.severity import assess_damage_severity
from services.priority import determine_maintenance_priority
from services.gradcam import generate_gradcam_visualization
from services.progression import analyze_historical_progression
from services.report_generator import generate_inspection_report_csv
from utils.gps_utils import extract_gps_coordinates
import cv2

router = APIRouter(prefix="/api/inspections", tags=["inspections"])

BASE_STORAGE = os.environ.get(
    "INFRASCAN_STORAGE_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)
UPLOAD_DIR = os.environ.get("INFRASCAN_UPLOAD_DIR", os.path.join(BASE_STORAGE, "uploads"))
RESULTS_DIR = os.environ.get("INFRASCAN_RESULTS_DIR", os.path.join(BASE_STORAGE, "results"))
REPORTS_DIR = os.environ.get("INFRASCAN_REPORTS_DIR", os.path.join(BASE_STORAGE, "reports"))
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

def build_inspection_response(insp: Inspection) -> dict:
    res = insp.results
    result_dict = None
    if res:
        reasons = []
        try:
            reasons = json.loads(res.severity_reasons_json)
        except Exception:
            reasons = [res.severity_reasons_json]

        detections = []
        try:
            detections = json.loads(res.detections_json)
        except Exception:
            detections = []

        model_status = {}
        try:
            model_status = json.loads(res.model_status_json)
        except Exception:
            model_status = {}

        result_dict = {
            "id": res.id,
            "inspection_id": res.inspection_id,
            "crack_detected": res.crack_detected,
            "crack_probability": res.crack_probability,
            "surface_type": res.surface_type,
            "defect_count": res.defect_count,
            "detections": detections,
            "mask_url": f"/static/results/{os.path.basename(res.mask_image_path)}" if res.mask_image_path else None,
            "overlay_url": f"/static/results/{os.path.basename(res.overlay_image_path)}" if res.overlay_image_path else None,
            "gradcam_url": f"/static/results/{os.path.basename(res.gradcam_image_path)}" if res.gradcam_image_path else None,
            "original_url": f"/static/uploads/{os.path.basename(insp.original_image_path)}",
            "crack_area_px": res.crack_area_px,
            "crack_area_ratio": res.crack_area_ratio,
            "skeleton_length_px": res.skeleton_length_px,
            "mean_width_px": res.mean_width_px,
            "max_width_px": res.max_width_px,
            "crack_density": res.crack_density,
            "orientation_angle": res.orientation_angle,
            "num_branches": res.num_branches,
            "num_components": res.num_components,
            "is_calibrated": res.is_calibrated,
            "estimated_length_mm": res.estimated_length_mm,
            "estimated_max_width_mm": res.estimated_max_width_mm,
            "severity_level": res.severity_level,
            "severity_score": res.severity_score,
            "severity_reasons": reasons,
            "urgent_review_required": res.urgent_review_required,
            "priority_level": res.priority_level,
            "priority_score": res.priority_score,
            "priority_rationale": res.priority_rationale,
            "recommended_action": res.recommended_action,
            "brightness_mean": res.brightness_mean,
            "contrast_std": res.contrast_std,
            "blur_score": res.blur_score,
            "is_blurry": res.is_blurry,
            "is_low_light": res.is_low_light,
            "image_width": res.image_width,
            "image_height": res.image_height,
            "model_status": model_status
        }

    return {
        "id": insp.id,
        "asset_id": insp.asset_id,
        "asset_name": insp.asset.name if insp.asset else "Unassigned",
        "user_id": insp.user_id,
        "user_username": insp.user.username if insp.user else "System / Legacy",
        "image_filename": insp.image_filename,
        "timestamp": insp.timestamp,
        "inspector_name": insp.inspector_name,
        "notes": insp.notes,
        "latitude": insp.latitude,
        "longitude": insp.longitude,
        "location_source": insp.location_source,
        "result": result_dict
    }

@router.get("")
@router.get("/")
def list_inspections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns inspections list.
    RBAC Rule: Regular users see ONLY their own private inspections.
    Admins have system-wide access to view all inspections.
    """
    if current_user.role == "admin":
        inspections = db.query(Inspection).order_by(Inspection.timestamp.desc()).all()
    else:
        inspections = db.query(Inspection).filter(
            Inspection.user_id == current_user.id
        ).order_by(Inspection.timestamp.desc()).all()

    return [build_inspection_response(i) for i in inspections]

@router.get("/{inspection_id}")
def get_inspection_detail(
    inspection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns inspection detail.
    RBAC Rule: Enforces ownership. A regular user cannot view another user's inspection.
    """
    insp = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(status_code=404, detail="Inspection record not found")

    if current_user.role != "admin" and insp.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not have permission to view another user's inspection record."
        )

    return build_inspection_response(insp)

@router.get("/{inspection_id}/report")
def download_inspection_report(
    inspection_id: int,
    format: str = Query("csv", regex="^(csv|pdf)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generates and downloads the inspection report in CSV or PDF format.
    RBAC Rule: Enforces strict ownership. Regular users cannot download another user's reports.
    """
    insp = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(status_code=404, detail="Inspection record not found")

    if current_user.role != "admin" and insp.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not have permission to download another user's inspection report."
        )

    res = insp.results
    if not res:
        raise HTTPException(status_code=400, detail="Inspection has no analysis results to export.")

    from services.report_generator import generate_inspection_report_pdf, generate_inspection_report_csv

    if format.lower() == "pdf":
        report_filename = f"InfraScan_Report_Insp_{insp.id}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
        report_path = os.path.join(REPORTS_DIR, report_filename)
        generate_inspection_report_pdf(insp, res, report_path)
        media_type = "application/pdf"
    else:
        report_filename = f"InfraScan_Report_Insp_{insp.id}_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        report_path = os.path.join(REPORTS_DIR, report_filename)
        generate_inspection_report_csv(insp, res, report_path)
        media_type = "text/csv"

    return FileResponse(
        path=report_path,
        filename=report_filename,
        media_type=media_type
    )

@router.post("/analyze")
async def analyze_inspection_image(
    image: UploadFile = File(...),
    asset_id: Optional[int] = Form(None),
    inspector_name: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    manual_latitude: Optional[float] = Form(None),
    manual_longitude: Optional[float] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Runs the full AI damage inspection pipeline:
    1. Image Quality Assessment
    2. Binary Crack Classification (CNN)
    3. Crack Semantic Segmentation (U-Net)
    4. Object Detection & Localization (YOLO11s on models/yolo_best.pt)
    5. Crack Geometry & Pixel Measurements
    6. Transparent Damage Severity Assessment
    7. Historical Progression Comparison
    8. Maintenance Prioritization
    9. Explainable AI (Grad-CAM Spatial Activation Mapping)
    
    Associates the inspection record with the authenticated user.
    """
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}
    ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/bmp", "image/webp", "image/tiff"}

    # 1. Pre-validation: Extension and MIME type check
    file_ext = os.path.splitext(image.filename)[1].lower() if image.filename else ""
    if file_ext not in ALLOWED_EXTENSIONS or (image.content_type and image.content_type.lower() not in ALLOWED_MIME_TYPES):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file format '{file_ext}'. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )

    upload_path = None
    mask_path = None
    overlay_path = None
    gradcam_path = None

    try:
        timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{timestamp_str}_{os.path.basename(image.filename)}"
        upload_path = os.path.join(UPLOAD_DIR, filename)

        contents = await image.read()
        if not contents or len(contents) < 32:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty or too small to be a valid image."
            )

        with open(upload_path, "wb") as buffer:
            buffer.write(contents)

        # 2. Content validation: Verify actual image decoding with OpenCV
        img_bgr = cv2.imread(upload_path)
        if img_bgr is None or img_bgr.size == 0:
            if os.path.exists(upload_path):
                os.remove(upload_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Corrupt or invalid image content. File cannot be decoded as an image."
            )

        # 3. Location handling
        gps_coords = extract_gps_coordinates(upload_path)
        final_lat = None
        final_lon = None
        loc_source = "none"

        if gps_coords:
            final_lat, final_lon = gps_coords
            loc_source = "exif_metadata"
        elif manual_latitude is not None and manual_longitude is not None:
            final_lat = manual_latitude
            final_lon = manual_longitude
            loc_source = "manual_entry"
        elif asset_id:
            asset = db.query(Asset).filter(Asset.id == asset_id).first()
            if asset and asset.latitude and asset.longitude:
                final_lat = asset.latitude
                final_lon = asset.longitude
                loc_source = "asset_default"

        # 4. Image Quality Assessment
        quality = assess_image_quality(img_bgr)

        # 5. Binary Crack Classification
        classification = run_crack_classification(img_bgr)

        # 6. Crack Semantic Segmentation
        mask_name = f"mask_{filename}.png"
        overlay_name = f"overlay_{filename}.png"
        mask_path = os.path.join(RESULTS_DIR, mask_name)
        overlay_path = os.path.join(RESULTS_DIR, overlay_name)

        mask, crack_area_px, crack_area_ratio = run_crack_segmentation(img_bgr, mask_path, overlay_path)

        # 5. Object Detection (Improved YOLO11s)
        detection = run_crack_detection(img_bgr, mask)

        # 6. Crack Geometry & Measurement Extraction
        geometry = extract_crack_geometry(mask)

        # 7. Damage Severity Assessment
        severity = assess_damage_severity(
            crack_detected=classification["crack_detected"],
            geometry=geometry,
            defect_count=detection["defect_count"],
            surface_type=classification["surface_type"]
        )

        # 8. Historical Progression Analysis
        progression = analyze_historical_progression(db, asset_id, geometry["crack_area_px"])

        # 9. Maintenance Prioritization
        asset_type = "Concrete Structure"
        if asset_id:
            asset = db.query(Asset).filter(Asset.id == asset_id).first()
            if asset:
                asset_type = asset.type

        priority = determine_maintenance_priority(
            severity=severity,
            asset_type=asset_type,
            historical_progression=progression
        )

        # 10. Explainable AI (Grad-CAM)
        gradcam_name = f"gradcam_{filename}.png"
        gradcam_path = os.path.join(RESULTS_DIR, gradcam_name)
        generate_gradcam_visualization(
            img_bgr,
            crack_detected=classification["crack_detected"],
            binary_mask=mask,
            output_path=gradcam_path
        )

        # Inspector Name: use user profile if not provided
        resolved_inspector = inspector_name.strip() if inspector_name and inspector_name.strip() else (current_user.full_name or current_user.username)

        # Create Inspection record associated with the authenticated user
        insp = Inspection(
            asset_id=asset_id,
            user_id=current_user.id,
            image_filename=filename,
            original_image_path=upload_path,
            inspector_name=resolved_inspector,
            notes=notes,
            latitude=final_lat,
            longitude=final_lon,
            location_source=loc_source
        )
        db.add(insp)
        db.commit()
        db.refresh(insp)

        # Model status
        model_status = {
            "classification": classification.get("model_status"),
            "detection": detection.get("model_status"),
            "segmentation": "U-Net Morphological & High-Fidelity Segmentation",
            "geometry": "Exact connected components & distance transform skeletonization",
            "explainability": "Grad-CAM spatial activation mapping"
        }

        # Create InspectionResult record
        res = InspectionResult(
            inspection_id=insp.id,
            crack_detected=classification["crack_detected"],
            crack_probability=classification["crack_probability"],
            surface_type=classification["surface_type"],
            classification_notes=classification.get("notes", ""),
            defect_count=detection["defect_count"],
            detections_json=json.dumps(detection["detections"]),
            mask_image_path=mask_path,
            overlay_image_path=overlay_path,
            crack_area_px=geometry["crack_area_px"],
            crack_area_ratio=geometry["crack_area_ratio"],
            skeleton_length_px=geometry["skeleton_length_px"],
            mean_width_px=geometry["mean_width_px"],
            max_width_px=geometry["max_width_px"],
            crack_density=geometry["crack_density"],
            orientation_angle=geometry["orientation_angle"],
            num_branches=geometry["num_branches"],
            num_components=geometry["num_components"],
            is_calibrated=False,
            severity_level=severity["severity_level"],
            severity_score=severity["severity_score"],
            severity_reasons_json=json.dumps(severity["severity_reasons"]),
            urgent_review_required=severity["urgent_review_required"],
            priority_level=priority["priority_level"],
            priority_score=priority["priority_score"],
            priority_rationale=priority["priority_rationale"],
            recommended_action=priority["recommended_action"],
            brightness_mean=quality["brightness_mean"],
            contrast_std=quality["contrast_std"],
            blur_score=quality["blur_score"],
            is_blurry=quality["is_blurry"],
            is_low_light=quality["is_low_light"],
            image_width=quality["image_width"],
            image_height=quality["image_height"],
            gradcam_image_path=gradcam_path,
            model_status_json=json.dumps(model_status)
        )
        db.add(res)
        db.commit()
        db.refresh(res)

        return build_inspection_response(insp)
    except HTTPException:
        # Re-raise explicit client HTTPExceptions (400, 415, etc.) without wrapping
        raise
    except Exception as exc:
        traceback.print_exc()
        # Clean up any partially created files on unexpected error
        for p in [upload_path, mask_path, overlay_path, gradcam_path]:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the inspection image. Please try again with a valid image."
        )
