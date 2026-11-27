from __future__ import annotations

from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import BASE_DIR, settings
from app.database import get_db
from app.deps import get_current_user
from app.models.asset import InfrastructureAsset
from app.models.damage import DamageAssessment
from app.models.image import Image as ImageModel
from app.models.inspection import Inspection
from app.models.report import InspectionReport
from app.models.user import User

from app.services.report_service import (
    generate_inspection_csv,
    generate_inspection_json,
    generate_inspection_pdf,
)


router = APIRouter(tags=["Inspection Reports"])


class ReportGenerateRequest(BaseModel):
    report_format: str = "pdf"  # pdf, csv, json


@router.post("/inspections/{inspection_id}/reports/generate", status_code=status.HTTP_201_CREATED)
def generate_report_endpoint(
    inspection_id: int,
    payload: ReportGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate an inspection report in PDF, CSV, or JSON format.
    Stores the artifact on disk and logs an InspectionReport entity.
    """
    inspection = db.query(Inspection).filter(Inspection.inspection_id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.asset_id == inspection.asset_id).first()
    images = db.query(ImageModel).filter(ImageModel.inspection_id == inspection_id).all()
    assessments = db.query(DamageAssessment).filter(DamageAssessment.inspection_id == inspection_id).all()

    fmt = payload.report_format.lower().strip()
    if fmt not in ["pdf", "csv", "json"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Format must be pdf, csv, or json")

    reports_dir = Path(settings.upload_path).parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    filename = f"inspection_report_{inspection_id}_{fmt}.{fmt}"
    output_disk_path = reports_dir / filename

    if fmt == "pdf":
        generate_inspection_pdf(inspection, asset, images, assessments, output_disk_path)
    elif fmt == "csv":
        generate_inspection_csv(inspection, asset, images, assessments, output_disk_path)
    elif fmt == "json":
        generate_inspection_json(inspection, asset, images, assessments, output_disk_path)

    file_size = output_disk_path.stat().st_size if output_disk_path.is_file() else 0

    # Calculate overall condition score (100 - avg severity score)
    avg_sev = sum([a.severity_score for a in assessments]) / len(assessments) if assessments else 0.0
    cond_score = round(max(0.0, 100.0 - avg_sev), 1)

    record = InspectionReport(
        inspection_id=inspection_id,
        generated_by=current_user.user_id,
        report_format=fmt,
        file_path=str(output_disk_path),
        file_size_bytes=file_size,
        overall_condition_score=cond_score,
        engineer_signoff=True if current_user.role in ["civil_engineer", "admin"] else False,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "report_id": record.report_id,
        "inspection_id": record.inspection_id,
        "report_format": record.report_format,
        "file_size_bytes": record.file_size_bytes,
        "overall_condition_score": record.overall_condition_score,
        "download_url": f"/api/reports/{record.report_id}/download",
        "created_at": record.created_at,
    }


@router.get("/reports/{report_id}/download")
def download_report_file(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download a generated inspection report file."""
    record = db.query(InspectionReport).filter(InspectionReport.report_id == report_id).first()
    if not record or not Path(record.file_path).is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file not found")

    media_types = {
        "pdf": "application/pdf",
        "csv": "text/csv",
        "json": "application/json",
    }
    media_type = media_types.get(record.report_format, "application/octet-stream")
    filename = Path(record.file_path).name

    return FileResponse(
        record.file_path,
        media_type=media_type,
        filename=filename,
    )


@router.get("/inspections/{inspection_id}/reports")
def list_inspection_reports(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all reports generated for an inspection."""
    reports = db.query(InspectionReport).filter(InspectionReport.inspection_id == inspection_id).order_by(InspectionReport.created_at.desc()).all()
    return [
        {
            "report_id": r.report_id,
            "report_format": r.report_format,
            "file_size_bytes": r.file_size_bytes,
            "overall_condition_score": r.overall_condition_score,
            "engineer_signoff": r.engineer_signoff,
            "download_url": f"/api/reports/{r.report_id}/download",
            "created_at": r.created_at,
        }
        for r in reports
    ]
