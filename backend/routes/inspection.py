import csv
import io
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.database import get_db, AssetRecord, InspectionRecord
from backend.services.classifier import classifier_service
from backend.services.report_generator import generate_pdf_report
from backend.services.segmenter import segmenter_service

router = APIRouter(prefix="/api", tags=["Inspection & Asset Management"])
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# --- Pydantic Schemas for Assets ---
class AssetCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    asset_type: str = Field(..., description="Bridge, Building, Road, Pavement, Concrete Structure, Other")
    location: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    asset_type: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None


# --- Asset Management Endpoints (Module 10) ---

@router.get("/assets", summary="List all registered infrastructure assets")
def list_assets(db: Session = Depends(get_db)):
    """Returns all registered infrastructure assets with associated inspection counts."""
    assets = db.query(AssetRecord).order_by(desc(AssetRecord.created_at)).all()
    results = []
    for a in assets:
        data = a.to_dict()
        data["inspection_count"] = db.query(InspectionRecord).filter(
            (InspectionRecord.asset_id == a.id) | (InspectionRecord.infrastructure_name == a.name)
        ).count()
        results.append(data)
    return results


@router.post("/assets", status_code=201, summary="Register a new infrastructure asset")
def create_asset(payload: AssetCreate, db: Session = Depends(get_db)):
    """Registers a new infrastructure asset into the persistent database."""
    asset_id = f"ASSET-{uuid.uuid4().hex[:6].upper()}"
    new_asset = AssetRecord(
        id=asset_id,
        name=payload.name,
        asset_type=payload.asset_type,
        location=payload.location,
        description=payload.description or "",
        created_at=datetime.utcnow()
    )
    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)
    return new_asset.to_dict()


@router.get("/assets/{asset_id}", summary="Get asset details")
def get_asset(asset_id: str, db: Session = Depends(get_db)):
    """Fetches details for a single asset."""
    asset = db.query(AssetRecord).filter(AssetRecord.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found.")
    data = asset.to_dict()
    data["inspections"] = [
        r.to_dict() for r in db.query(InspectionRecord).filter(
            (InspectionRecord.asset_id == asset.id) | (InspectionRecord.infrastructure_name == asset.name)
        ).order_by(desc(InspectionRecord.timestamp)).all()
    ]
    return data


@router.put("/assets/{asset_id}", summary="Update asset details")
def update_asset(asset_id: str, payload: AssetUpdate, db: Session = Depends(get_db)):
    """Updates fields for an existing asset."""
    asset = db.query(AssetRecord).filter(AssetRecord.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found.")
    if payload.name:
        asset.name = payload.name
    if payload.asset_type:
        asset.asset_type = payload.asset_type
    if payload.location:
        asset.location = payload.location
    if payload.description is not None:
        asset.description = payload.description
    db.commit()
    return asset.to_dict()


@router.delete("/assets/{asset_id}", summary="Delete an asset")
def delete_asset(asset_id: str, db: Session = Depends(get_db)):
    """Deletes an asset record."""
    asset = db.query(AssetRecord).filter(AssetRecord.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found.")
    db.delete(asset)
    db.commit()
    return {"status": "success", "message": f"Asset '{asset_id}' deleted successfully."}


@router.get("/assets/{asset_id}/inspections", summary="Get inspections for an asset")
def get_asset_inspections(asset_id: str, db: Session = Depends(get_db)):
    """Returns all inspections associated with an asset."""
    asset = db.query(AssetRecord).filter(AssetRecord.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found.")
    records = db.query(InspectionRecord).filter(
        (InspectionRecord.asset_id == asset.id) | (InspectionRecord.infrastructure_name == asset.name)
    ).order_by(desc(InspectionRecord.timestamp)).all()
    return [r.to_dict() for r in records]


# --- Dashboard & Analytics Endpoints (Module 5 & Module 11) ---

@router.get("/dashboard/stats", summary="Get aggregate dashboard statistics")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Computes real live statistics directly from the database."""
    total_assets = db.query(AssetRecord).count()
    total_inspections = db.query(InspectionRecord).count()
    cracked = db.query(InspectionRecord).filter(InspectionRecord.classification_label == "Cracked").count()
    uncracked = total_inspections - cracked
    rate = round((cracked / total_inspections * 100), 2) if total_inspections > 0 else 0.0

    # Severity distribution
    severities = {"None": 0, "Low": 0, "Moderate": 0, "High": 0}
    for rec in db.query(InspectionRecord.severity_level).all():
        sev = rec[0]
        if sev in severities:
            severities[sev] += 1
        else:
            severities[sev] = 1

    # High priority findings count
    high_priority = db.query(InspectionRecord).filter(
        (InspectionRecord.severity_level == "High") | (InspectionRecord.suggested_priority.in_(["High", "Urgent"]))
    ).count()

    # Recent 10 inspections
    recent_records = (
        db.query(InspectionRecord)
        .order_by(desc(InspectionRecord.timestamp))
        .limit(10)
        .all()
    )
    recent = [r.to_dict() for r in recent_records]

    return {
        "total_assets": total_assets,
        "total_inspections": total_inspections,
        "cracked_count": cracked,
        "uncracked_count": uncracked,
        "crack_detection_rate": rate,
        "high_priority_count": high_priority,
        "severity_distribution": severities,
        "recent_inspections": recent,
        "models_ready": classifier_service.is_loaded() and segmenter_service.is_loaded()
    }


@router.get("/analytics", summary="Get detailed analytics and chart datasets")
def get_analytics(db: Session = Depends(get_db)):
    """Returns aggregated datasets for Chart.js analytics graphs."""
    inspections = db.query(InspectionRecord).all()
    
    total = len(inspections)
    cracked = sum(1 for i in inspections if i.classification_label == "Cracked")
    uncracked = total - cracked

    # Severity distribution
    severity_counts = {"None": 0, "Low": 0, "Moderate": 0, "High": 0}
    for i in inspections:
        sev = i.severity_level or "None"
        if sev in severity_counts:
            severity_counts[sev] += 1
        else:
            severity_counts[sev] = 1

    # Infrastructure type breakdown
    type_counts = {}
    for i in inspections:
        t = i.infrastructure_type or "Concrete Structure"
        type_counts[t] = type_counts.get(t, 0) + 1

    # Activity over time (grouped by date)
    daily_activity = {}
    for i in inspections:
        d_str = i.timestamp.strftime("%Y-%m-%d") if i.timestamp else datetime.utcnow().strftime("%Y-%m-%d")
        daily_activity[d_str] = daily_activity.get(d_str, 0) + 1

    # High priority count
    high_priority = sum(1 for i in inspections if i.severity_level == "High" or i.suggested_priority in ["High", "Urgent"])

    return {
        "total_inspections": total,
        "crack_ratio": {
            "labels": ["Cracked Concrete", "Intact Surface"],
            "data": [cracked, uncracked]
        },
        "severity_distribution": {
            "labels": list(severity_counts.keys()),
            "data": list(severity_counts.values())
        },
        "infrastructure_summary": {
            "labels": list(type_counts.keys()) if type_counts else ["Bridge", "Pavement", "Building"],
            "data": list(type_counts.values()) if type_counts else [0, 0, 0]
        },
        "activity_timeline": {
            "labels": sorted(list(daily_activity.keys())),
            "data": [daily_activity[k] for k in sorted(list(daily_activity.keys()))]
        },
        "high_priority_count": high_priority
    }


# --- Inspection History & Reports Endpoints (Module 9 & Module 13) ---

@router.get("/inspections", summary="List inspection history with search and filter")
def list_inspections(
    search: Optional[str] = Query(None, description="Search by ID, infrastructure name, location, or inspector"),
    crack_status: Optional[str] = Query(None, description="Filter by 'Cracked' or 'Uncracked'"),
    severity: Optional[str] = Query(None, description="Filter by severity level"),
    infrastructure_type: Optional[str] = Query(None, description="Filter by infrastructure type"),
    sort_by: Optional[str] = Query("timestamp", description="Sort by 'timestamp', 'confidence', or 'crack_percentage'"),
    order: Optional[str] = Query("desc", description="Sort order 'desc' or 'asc'"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Returns paginated, searchable, filterable historical inspection records."""
    query = db.query(InspectionRecord)

    if search:
        s_term = f"%{search}%"
        query = query.filter(
            (InspectionRecord.id.ilike(s_term)) | 
            (InspectionRecord.infrastructure_name.ilike(s_term)) |
            (InspectionRecord.location.ilike(s_term)) |
            (InspectionRecord.inspector_name.ilike(s_term))
        )

    if crack_status and crack_status != "All":
        query = query.filter(InspectionRecord.classification_label == crack_status)

    if severity and severity != "All":
        query = query.filter(InspectionRecord.severity_level == severity)

    if infrastructure_type and infrastructure_type != "All":
        query = query.filter(InspectionRecord.infrastructure_type == infrastructure_type)

    total = query.count()

    # Determine sorting column
    sort_col = InspectionRecord.timestamp
    if sort_by == "confidence":
        sort_col = InspectionRecord.confidence
    elif sort_by == "crack_percentage":
        sort_col = InspectionRecord.crack_percentage

    if order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    records = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "inspections": [r.to_dict() for r in records]
    }


@router.get("/inspections/{inspection_id}", summary="Get single inspection record")
def get_inspection(inspection_id: str, db: Session = Depends(get_db)):
    """Fetches full inspection record by ID."""
    record = db.query(InspectionRecord).filter(InspectionRecord.id == inspection_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Inspection record '{inspection_id}' not found.")
    return record.to_dict()


@router.delete("/inspections/{inspection_id}", summary="Delete an inspection record")
def delete_inspection(inspection_id: str, db: Session = Depends(get_db)):
    """Deletes an inspection record from the database."""
    record = db.query(InspectionRecord).filter(InspectionRecord.id == inspection_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Inspection record '{inspection_id}' not found.")
    
    db.delete(record)
    db.commit()
    return {"status": "success", "message": f"Inspection record '{inspection_id}' deleted successfully."}


@router.get("/inspections/{inspection_id}/report", summary="Download PDF inspection report")
def download_inspection_report(inspection_id: str, db: Session = Depends(get_db)):
    """Generates and streams a PDF inspection report."""
    record = db.query(InspectionRecord).filter(InspectionRecord.id == inspection_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Inspection record '{inspection_id}' not found.")

    pdf_buffer = generate_pdf_report(record.to_dict())
    filename = f"{inspection_id}_Report.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/inspections/export/csv", summary="Export all inspections to CSV")
def export_inspections_csv(db: Session = Depends(get_db)):
    """Exports all stored inspections to a downloadable CSV spreadsheet."""
    records = db.query(InspectionRecord).order_by(desc(InspectionRecord.timestamp)).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "Inspection ID",
        "Asset ID",
        "Infrastructure Name",
        "Infrastructure Type",
        "Location",
        "Inspector",
        "Timestamp",
        "Filename",
        "Classification",
        "Confidence (%)",
        "Crack Probability",
        "Segmentation Result",
        "Crack Pixels",
        "Crack Percentage (%)",
        "Severity Level",
        "Suggested Priority",
        "Summary Advisory"
    ])
    
    for r in records:
        writer.writerow([
            r.id,
            r.asset_id or "",
            r.infrastructure_name or "",
            r.infrastructure_type or "",
            r.location or "",
            r.inspector_name or "",
            r.timestamp.isoformat() if r.timestamp else "",
            r.filename,
            r.classification_label,
            f"{r.confidence * 100:.2f}",
            f"{r.crack_probability:.4f}",
            r.segmentation_label,
            r.crack_pixel_count,
            f"{r.crack_percentage:.2f}",
            r.severity_level,
            r.suggested_priority or "Normal",
            r.summary
        ])
        
    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=infrascan_inspections_export.csv"}
    )


@router.get("/sample-image", summary="Get sample test concrete image for 1-click demo")
def get_sample_image(type: str = Query("cracked", pattern="^(cracked|uncracked)$")):
    """Returns a sample concrete image path from the verified dataset."""
    if type == "cracked":
        sample_dir = PROJECT_ROOT / "dataset" / "CRACK500" / "testcrop" / "testcrop"
        candidates = list(sample_dir.glob("*.jpg"))
    else:
        sample_dir = PROJECT_ROOT / "dataset" / "SDNET2018" / "D" / "UD"
        candidates = list(sample_dir.glob("*.jpg"))

    if not candidates:
        raise HTTPException(status_code=404, detail="No sample images found in dataset.")

    sample_path = candidates[0]
    return FileResponse(
        path=str(sample_path),
        media_type="image/jpeg",
        filename=sample_path.name
    )
