import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.inspection import Inspection
from app.models.report import Report, ReportFile
from app.models.user import User
from app.schemas.report import CreateReportRequest, PaginatedReportsResponse, ReportResponse
from app.services.report_service import (
    create_inspection_report,
    export_asset_summary,
    export_portfolio_summary,
)
from app.services.event_service import publish
from app.services.notification_service import create_notification

router = APIRouter(tags=["Reports & Exports"])


def check_inspection_access(inspection: Inspection, user: User) -> None:
    """Ensure user has permission to view/generate reports for this inspection."""
    if user.role in ("admin", "civil_engineer", "manager"):
        return
    if user.role == "inspector" and inspection.inspector_id == user.user_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have access to reports for this inspection.",
    )


# 1. POST /inspections/{inspection_id}/reports - Generate a new report version
@router.post(
    "/inspections/{inspection_id}/reports",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_report(
    inspection_id: int,
    req: CreateReportRequest = CreateReportRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate an immutable versioned report snapshot for an inspection."""
    inspection = db.query(Inspection).filter(Inspection.inspection_id == inspection_id).first()
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection #{inspection_id} not found",
        )

    check_inspection_access(inspection, current_user)

    try:
        report = create_inspection_report(
            db=db,
            inspection_id=inspection_id,
            user=current_user,
            notes=req.notes,
        )
        publish(
            db=db,
            event_type="report.ready",
            entity_type="report",
            entity_id=report.report_id,
            audience={
                "roles": ["admin", "manager", "civil_engineer"],
                "inspector_id": inspection.inspector_id,
            },
            payload={
                "report_id": report.report_id,
                "inspection_id": inspection_id,
                "status": report.status,
                "version": report.version,
            },
        )
        create_notification(
            db=db,
            user_id=current_user.user_id,
            type="report_ready",
            title="Inspection Report Ready",
            body=f"Report v{report.version} ({report.status.upper()}) for inspection #{inspection_id} is ready for download.",
            entity_type="report",
            entity_id=str(report.report_id),
            severity="medium",
        )
        managers = db.query(User).filter(User.role == "manager", User.is_active == True).all()
        for mgr in managers:
            if mgr.user_id != current_user.user_id:
                create_notification(
                    db=db,
                    user_id=mgr.user_id,
                    type="report_ready",
                    title="Inspection Report Ready",
                    body=f"Report v{report.version} ({report.status.upper()}) for inspection #{inspection_id} is ready for download.",
                    entity_type="report",
                    entity_id=str(report.report_id),
                    severity="medium",
                )
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}",
        )


# 2. GET /reports - List reports with filtering and pagination
@router.get("/reports", response_model=PaginatedReportsResponse)
def list_reports(
    inspection_id: Optional[int] = Query(None, description="Filter by inspection ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (draft/final)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List reports accessible to the current user."""
    query = db.query(Report).join(Inspection, Report.inspection_id == Inspection.inspection_id)

    # RBAC: Inspectors only see reports for their assigned inspections
    if current_user.role == "inspector":
        query = query.filter(Inspection.inspector_id == current_user.user_id)

    if inspection_id:
        query = query.filter(Report.inspection_id == inspection_id)
    if status_filter:
        query = query.filter(Report.status == status_filter)

    total = query.count()
    items = (
        query.order_by(Report.report_id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedReportsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# 3. GET /reports/{report_id} - Get report details
@router.get("/reports/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve metadata and generated files for a single report."""
    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report #{report_id} not found",
        )

    inspection = db.query(Inspection).filter(Inspection.inspection_id == report.inspection_id).first()
    if inspection:
        check_inspection_access(inspection, current_user)

    return report


# 4. GET /reports/{report_id}/download - Download specific format (pdf, csv, xlsx, json)
@router.get("/reports/{report_id}/download")
def download_report(
    report_id: int,
    format: str = Query("pdf", pattern="^(pdf|csv|xlsx|json)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download a generated report in PDF, CSV bundle, Excel, or JSON format."""
    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report #{report_id} not found",
        )

    inspection = db.query(Inspection).filter(Inspection.inspection_id == report.inspection_id).first()
    if inspection:
        check_inspection_access(inspection, current_user)

    report_file = (
        db.query(ReportFile)
        .filter(ReportFile.report_id == report_id, ReportFile.format == format.lower())
        .first()
    )
    if not report_file or not os.path.exists(report_file.path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report format '{format}' not found or file missing on disk.",
        )

    media_types = {
        "pdf": "application/pdf",
        "csv": "application/zip",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "json": "application/json",
    }
    media_type = media_types.get(format.lower(), "application/octet-stream")
    filename = os.path.basename(report_file.path)

    return FileResponse(
        path=report_file.path,
        media_type=media_type,
        filename=filename,
    )


# 5. GET /assets/{asset_id}/export - Asset inspection summary export (CSV or Excel)
@router.get("/assets/{asset_id}/export")
def export_asset(
    asset_id: int,
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export asset inspection and defect history as CSV or Excel."""
    try:
        content, filename, media_type = export_asset_summary(db=db, asset_id=asset_id, format=format)
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export asset summary: {str(e)}",
        )


# 6. GET /exports/portfolio - Portfolio-wide export across all assets (CSV or Excel)
@router.get("/exports/portfolio")
def export_portfolio(
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    current_user: User = Depends(require_roles("admin", "civil_engineer", "manager")),
    db: Session = Depends(get_db),
):
    """Export complete portfolio-level summary across all assets as CSV or Excel."""
    try:
        content, filename, media_type = export_portfolio_summary(db=db, format=format)
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export portfolio summary: {str(e)}",
        )
