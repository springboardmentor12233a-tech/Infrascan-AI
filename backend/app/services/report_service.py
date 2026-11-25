import csv
import hashlib
import io
import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import jsonschema
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import BASE_DIR, settings
from app.models.analysis import AnalysisRun, CrackMeasurement, Detection, ImageScale, ModelVersion
from app.models.asset import InfrastructureAsset
from app.models.explanation import Explanation
from app.models.image import Image
from app.models.inspection import Inspection
from app.models.maintenance import MaintenancePriority, MaintenanceTask
from app.models.report import Report, ReportFile
from app.models.severity import InspectionSeverity, SeverityAssessment
from app.models.user import User
from app.services.audit import create_audit_log

# Load JSON schema once
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "report_snapshot.schema.json"


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print total page count and footer disclaimers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Header rule
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(40, 755, 572, 755)

        # Header text
        self.drawString(40, 760, "InfraScan — Automated Structural Health & Defect Assessment Report")
        status_text = getattr(self, "report_status_text", "DRAFT")
        self.drawRightString(572, 760, status_text)

        # Footer rule
        self.line(40, 45, 572, 45)

        # Footer text & disclaimer
        disclaimer = "AI result for engineer review, not a final structural safety verdict."
        self.drawString(40, 32, disclaimer)
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(572, 32, page_str)

        # Watermark on draft reports
        if getattr(self, "is_draft_watermark", False):
            self.saveState()
            self.setFont("Helvetica-Bold", 42)
            self.setFillColor(colors.HexColor("#FEE2E2"), alpha=0.35)
            self.translate(306, 396)
            self.rotate(45)
            self.drawCentredString(0, 0, "DRAFT - PENDING ENGINEER REVIEW")
            self.restoreState()

        self.restoreState()


def get_file_sha256(file_path: Path) -> str:
    """Compute SHA256 hex digest of a file on disk."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def sanitize_csv_cell(val: Any) -> Any:
    """Protect against CSV formula injection by prepending apostrophe to =, +, -, @."""
    if val is None:
        return ""
    s = str(val)
    if s.startswith(("=", "+", "-", "@")):
        return "'" + s
    return s


def build_inspection_snapshot(
    db: Session,
    inspection_id: int,
    user: User,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Extract complete database snapshot for an inspection and validate against JSON Schema."""
    inspection = db.query(Inspection).filter(Inspection.inspection_id == inspection_id).first()
    if not inspection:
        raise ValueError(f"Inspection #{inspection_id} not found.")

    asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.asset_id == inspection.asset_id).first()
    inspector = db.query(User).filter(User.user_id == inspection.inspector_id).first() if inspection.inspector_id else None

    # Images
    images_records = (
        db.query(Image)
        .filter(Image.inspection_id == inspection_id)
        .order_by(Image.image_id.asc())
        .all()
    )

    all_reviewed = True
    images_data: List[Dict[str, Any]] = []
    total_detections = 0
    worst_severity = "none"
    worst_score = 0.0
    severity_order = {"none": 0, "minor": 1, "moderate": 2, "severe": 3, "critical": 4}

    for img in images_records:
        # Latest AnalysisRun
        latest_run = (
            db.query(AnalysisRun)
            .filter(AnalysisRun.image_id == img.image_id)
            .order_by(AnalysisRun.run_id.desc())
            .first()
        )

        detections_list: List[Dict[str, Any]] = []
        measurements_dict: Optional[Dict[str, Any]] = None
        severity_dict: Optional[Dict[str, Any]] = None
        scale_dict: Optional[Dict[str, Any]] = None
        explanations_list: List[Dict[str, Any]] = []

        if latest_run:
            # Detections
            dets = db.query(Detection).filter(Detection.run_id == latest_run.run_id).all()
            total_detections += len(dets)
            for d in dets:
                detections_list.append({
                    "detection_id": d.detection_id,
                    "model_id": d.model_id,
                    "damage_type": d.damage_type,
                    "damage_label": d.damage_label,
                    "confidence": float(d.confidence) if d.confidence else 0.0,
                    "box": [float(d.x_min or 0), float(d.y_min or 0), float(d.x_max or 0), float(d.y_max or 0)],
                })

            # Measurements
            meas = db.query(CrackMeasurement).filter(CrackMeasurement.run_id == latest_run.run_id).first()
            if meas:
                measurements_dict = {
                    "measurement_id": meas.measurement_id,
                    "crack_pixels": meas.crack_pixels,
                    "length_px": float(meas.length_px) if meas.length_px else None,
                    "avg_width_px": float(meas.avg_width_px) if meas.avg_width_px else None,
                    "max_width_px": float(meas.max_width_px) if meas.max_width_px else None,
                    "p95_width_px": float(meas.p95_width_px) if meas.p95_width_px else None,
                    "area_px": float(meas.area_px) if meas.area_px else None,
                    "density_percent": float(meas.density_percent) if meas.density_percent else None,
                    "orientation_deg": float(meas.orientation_deg) if meas.orientation_deg else None,
                    # mm values only when scale is present
                    "mm_per_pixel": float(meas.mm_per_pixel) if meas.mm_per_pixel else None,
                    "length_mm": float(meas.length_mm) if meas.length_mm else None,
                    "avg_width_mm": float(meas.avg_width_mm) if meas.avg_width_mm else None,
                    "max_width_mm": float(meas.max_width_mm) if meas.max_width_mm else None,
                    "length_mm_uncertainty": float(meas.length_mm_uncertainty) if meas.length_mm_uncertainty else None,
                    "width_mm_uncertainty": float(meas.width_mm_uncertainty) if meas.width_mm_uncertainty else None,
                    "measurement_note": meas.measurement_note,
                }

            # Severity assessment
            sev = (
                db.query(SeverityAssessment)
                .filter(SeverityAssessment.image_id == img.image_id, SeverityAssessment.is_superseded == False)
                .order_by(SeverityAssessment.assessment_id.desc())
                .first()
            )
            if sev:
                sev_level = sev.final_severity or sev.severity_level
                sev_score = float(sev.score or 0.0)
                if severity_order.get(sev_level, 0) > severity_order.get(worst_severity, 0):
                    worst_severity = sev_level
                if sev_score > worst_score:
                    worst_score = sev_score

                is_reviewed = sev.review_status in ("confirmed", "corrected", "approved")
                if not is_reviewed:
                    all_reviewed = False

                severity_dict = {
                    "assessment_id": sev.assessment_id,
                    "severity_level": sev.severity_level,
                    "score": sev_score,
                    "priority_suggestion": sev.priority_suggestion,
                    "review_status": sev.review_status,
                    "final_severity": sev.final_severity,
                    "final_priority": sev.final_priority,
                    "reviewed_by": sev.reviewed_by,
                    "reviewed_at": sev.reviewed_at.isoformat() if sev.reviewed_at else None,
                    "review_comment": sev.review_comment,
                    "rules_version": sev.rules_version,
                    "rules_sha256": sev.rules_sha256,
                    "factors": json.loads(sev.factors_json) if sev.factors_json else [],
                    "warnings": json.loads(sev.warnings_json) if sev.warnings_json else [],
                }
            else:
                all_reviewed = False

            # Scale
            scale = db.query(ImageScale).filter(ImageScale.image_id == img.image_id, ImageScale.is_current == True).first()
            if scale:
                scale_dict = {
                    "scale_id": scale.scale_id,
                    "method": scale.method,
                    "mm_per_pixel": float(scale.mm_per_pixel) if scale.mm_per_pixel is not None else None,
                    "reference_mm": float(scale.reference_mm) if scale.reference_mm is not None else None,
                    "reference_px": float(scale.reference_px) if scale.reference_px is not None else None,
                    "uncertainty_percent": float(scale.uncertainty_percent) if scale.uncertainty_percent is not None else 0.0,
                }

            # Explanations
            exps = db.query(Explanation).filter(Explanation.image_id == img.image_id).all()
            for exp in exps:
                explanations_list.append({
                    "explanation_id": exp.explanation_id,
                    "model_id": exp.model_id,
                    "method": exp.method,
                    "target": exp.target,
                    "heatmap_path": exp.heatmap_path,
                    "overlay_path": exp.overlay_path,
                    "seconds": float(exp.seconds) if exp.seconds else None,
                })
        else:
            all_reviewed = False

        images_data.append({
            "image_id": img.image_id,
            "filename": img.original_filename,
            "file_path": img.file_path,
            "status": img.quality_status,
            "width_px": img.width_px,
            "height_px": img.height_px,
            "blur_score": float(img.blur_score) if img.blur_score else None,
            "brightness_score": float(img.brightness_score) if img.brightness_score else None,
            "gps_latitude": float(img.gps_latitude) if img.gps_latitude else None,
            "gps_longitude": float(img.gps_longitude) if img.gps_longitude else None,
            "detections": detections_list,
            "measurements": measurements_dict,
            "severity": severity_dict,
            "scale": scale_dict,
            "explanations": explanations_list,
        })

    # Models metadata
    models_records = db.query(ModelVersion).filter(ModelVersion.is_active == True).all()
    models_list = [
        {
            "model_id": m.model_id,
            "model_name": m.model_name,
            "task": m.task,
            "version": m.version,
            "metrics": json.loads(m.metrics_json) if m.metrics_json else {},
        }
        for m in models_records
    ]

    # Inspection severity summary
    insp_sev = db.query(InspectionSeverity).filter(InspectionSeverity.inspection_id == inspection_id).first()
    pending_count = sum(1 for img in images_data if not img.get("severity") or img["severity"].get("review_status") == "pending")

    status = "final" if (all_reviewed and len(images_data) > 0) else "draft"

    snapshot = {
        "schema_version": "1.0.0",
        "report_id": 0,  # Updated after report row created
        "inspection_id": inspection_id,
        "version": 1,
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": {
            "user_id": user.user_id,
            "name": user.full_name,
            "email": user.email,
            "role": user.role,
        },
        "notes": notes,
        "asset": {
            "asset_id": asset.asset_id if asset else 0,
            "name": asset.name if asset else "Unknown Asset",
            "asset_type": asset.asset_type if asset else "other",
            "material_type": asset.material_type if asset else "concrete",
            "address": asset.address if asset else None,
            "latitude": float(asset.latitude) if asset and asset.latitude else None,
            "longitude": float(asset.longitude) if asset and asset.longitude else None,
            "construction_year": asset.construction_year if asset else None,
            "responsible_department": asset.responsible_department if asset else None,
            "importance_level": asset.importance_level if asset else "medium",
            "district": getattr(asset, "district", None) if asset else None,
        },
        "inspection": {
            "inspection_id": inspection.inspection_id,
            "inspection_date": inspection.inspection_date.isoformat() if hasattr(inspection.inspection_date, "isoformat") else str(inspection.inspection_date),
            "status": inspection.status,
            "inspector": {
                "user_id": inspector.user_id,
                "name": inspector.full_name,
                "email": inspector.email,
            } if inspector else None,
        },
        "summary": {
            "total_images": len(images_data),
            "analyzed_images": sum(1 for img in images_data if img.get("measurements") or len(img.get("detections", [])) > 0),
            "total_detections": total_detections,
            "worst_severity": worst_severity,
            "worst_score": worst_score,
            "priority": "P1" if worst_severity in ("severe", "critical") else "P2" if worst_severity == "moderate" else "P3",
            "is_fully_reviewed": all_reviewed and len(images_data) > 0,
            "pending_reviews": pending_count,
        },
        "images": images_data,
        "models": models_list,
        "disclaimers": [
            "AI result for engineer review, not a final structural safety verdict.",
            "No damage detected by the AI. This is not evidence that there is no damage.",
            "Measurements are reported in pixels; millimetres are computed only when an authenticated scale reference is stored, with calculated uncertainty.",
            "All model metrics are extracted from registered VALIDATION or TEST splits exactly as evaluated.",
        ],
    }

    maintenance_tasks = (
        db.query(MaintenanceTask)
        .filter(MaintenanceTask.inspection_id == inspection_id)
        .all()
    )
    snapshot["maintenance_tasks"] = [
        {
            "task_id": t.task_id,
            "title": t.title,
            "description": t.description,
            "task_type": t.task_type,
            "priority": t.priority,
            "status": t.status,
            "due_date": t.due_date.isoformat() if t.due_date else None,
        }
        for t in maintenance_tasks
    ]

    return snapshot


def generate_json_file(snapshot: Dict[str, Any], output_path: Path) -> Tuple[int, str]:
    """Write validated JSON snapshot file to disk, returning (size, sha256)."""
    # Validate against JSON schema
    if SCHEMA_PATH.exists():
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = json.load(f)
        jsonschema.validate(instance=snapshot, schema=schema)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(snapshot, indent=2, sort_keys=True).encode("utf-8")
    with open(output_path, "wb") as f:
        f.write(content)
    size = len(content)
    sha256 = hashlib.sha256(content).hexdigest()
    return size, sha256


def generate_csv_bundle(snapshot: Dict[str, Any], output_dir: Path) -> Tuple[Path, int, str]:
    """Generate CSV tables with UTF-8 BOM and formula injection protection, packaged as a zip bundle."""
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"inspection_{snapshot['inspection_id']}_v{snapshot['version']}_csv.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. summary.csv
        sum_out = io.StringIO()
        sum_writer = csv.writer(sum_out)
        sum_writer.writerow(["# InfraScan Inspection Summary Report"])
        sum_writer.writerow(["# Disclaimer: AI result for engineer review, not a final structural safety verdict."])
        sum_writer.writerow(["Inspection ID", snapshot.get("inspection_id")])
        sum_writer.writerow(["Status", snapshot.get("status")])
        sum_writer.writerow(["Version", snapshot.get("version")])
        sum_writer.writerow(["Generated At", snapshot.get("generated_at")])
        sum_writer.writerow(["Asset ID", snapshot.get("asset", {}).get("asset_id")])
        sum_writer.writerow(["Asset Name", sanitize_csv_cell(snapshot.get("asset", {}).get("name"))])
        sum_writer.writerow(["Asset Type", sanitize_csv_cell(snapshot.get("asset", {}).get("asset_type"))])
        sum_writer.writerow(["Material", sanitize_csv_cell(snapshot.get("asset", {}).get("material_type"))])
        sum_writer.writerow(["Worst Severity", snapshot.get("summary", {}).get("worst_severity")])
        sum_writer.writerow(["Worst Score", snapshot.get("summary", {}).get("worst_score")])
        sum_writer.writerow(["Total Images", snapshot.get("summary", {}).get("total_images")])
        sum_writer.writerow(["Total Detections", snapshot.get("summary", {}).get("total_detections")])
        sum_writer.writerow(["Is Fully Reviewed", snapshot.get("summary", {}).get("is_fully_reviewed")])
        zf.writestr("summary.csv", ("\ufeff" + sum_out.getvalue()).encode("utf-8"))

        # 2. images.csv
        img_out = io.StringIO()
        img_writer = csv.writer(img_out)
        img_writer.writerow(["image_id", "filename", "status", "width_px", "height_px", "blur_score", "brightness_score", "gps_lat", "gps_lon"])
        for img in snapshot.get("images", []):
            img_writer.writerow([
                img.get("image_id"),
                sanitize_csv_cell(img.get("filename")),
                sanitize_csv_cell(img.get("status")),
                img.get("width_px"),
                img.get("height_px"),
                img.get("blur_score"),
                img.get("brightness_score"),
                img.get("gps_latitude"),
                img.get("gps_longitude"),
            ])
        zf.writestr("images.csv", ("\ufeff" + img_out.getvalue()).encode("utf-8"))

        # 3. detections.csv
        det_out = io.StringIO()
        det_writer = csv.writer(det_out)
        det_writer.writerow(["detection_id", "image_id", "model_id", "damage_type", "damage_label", "confidence", "box_xmin", "box_ymin", "box_xmax", "box_ymax"])
        for img in snapshot.get("images", []):
            for d in img.get("detections", []):
                box = d.get("box", [0, 0, 0, 0])
                det_writer.writerow([
                    d.get("detection_id"),
                    img.get("image_id"),
                    sanitize_csv_cell(d.get("model_id")),
                    sanitize_csv_cell(d.get("damage_type")),
                    sanitize_csv_cell(d.get("damage_label")),
                    d.get("confidence"),
                    box[0], box[1], box[2], box[3],
                ])
        zf.writestr("detections.csv", ("\ufeff" + det_out.getvalue()).encode("utf-8"))

        # 4. measurements.csv
        meas_out = io.StringIO()
        meas_writer = csv.writer(meas_out)
        meas_writer.writerow(["measurement_id", "image_id", "crack_pixels", "length_px", "avg_width_px", "max_width_px", "area_px", "density_pct", "mm_per_pixel", "length_mm", "avg_width_mm", "uncertainty_pct"])
        for img in snapshot.get("images", []):
            m = img.get("measurements")
            if m:
                meas_writer.writerow([
                    m.get("measurement_id"),
                    img.get("image_id"),
                    m.get("crack_pixels"),
                    m.get("length_px"),
                    m.get("avg_width_px"),
                    m.get("max_width_px"),
                    m.get("area_px"),
                    m.get("density_percent"),
                    m.get("mm_per_pixel"),
                    m.get("length_mm"),
                    m.get("avg_width_mm"),
                    m.get("length_mm_uncertainty"),
                ])
        zf.writestr("measurements.csv", ("\ufeff" + meas_out.getvalue()).encode("utf-8"))

        # 5. severity.csv
        sev_out = io.StringIO()
        sev_writer = csv.writer(sev_out)
        sev_writer.writerow(["assessment_id", "image_id", "severity_level", "score", "priority_suggestion", "review_status", "final_severity", "final_priority", "rules_version"])
        for img in snapshot.get("images", []):
            s = img.get("severity")
            if s:
                sev_writer.writerow([
                    s.get("assessment_id"),
                    img.get("image_id"),
                    sanitize_csv_cell(s.get("severity_level")),
                    s.get("score"),
                    sanitize_csv_cell(s.get("priority_suggestion")),
                    sanitize_csv_cell(s.get("review_status")),
                    sanitize_csv_cell(s.get("final_severity")),
                    sanitize_csv_cell(s.get("final_priority")),
                    sanitize_csv_cell(s.get("rules_version")),
                ])
        zf.writestr("severity.csv", ("\ufeff" + sev_out.getvalue()).encode("utf-8"))

        # 6. maintenance.csv
        maint_out = io.StringIO()
        maint_writer = csv.writer(maint_out)
        maint_writer.writerow(["task_id", "title", "description", "task_type", "priority", "status", "due_date"])
        for t in snapshot.get("maintenance_tasks", []):
            maint_writer.writerow([
                t.get("task_id"),
                sanitize_csv_cell(t.get("title")),
                sanitize_csv_cell(t.get("description")),
                sanitize_csv_cell(t.get("task_type")),
                sanitize_csv_cell(t.get("priority")),
                sanitize_csv_cell(t.get("status")),
                t.get("due_date"),
            ])
        zf.writestr("maintenance.csv", ("\ufeff" + maint_out.getvalue()).encode("utf-8"))

    size = os.path.getsize(zip_path)
    sha256 = get_file_sha256(zip_path)
    return zip_path, size, sha256


def generate_excel_file(snapshot: Dict[str, Any], output_path: Path) -> Tuple[int, str]:
    """Generate structured multi-tab Excel workbook using openpyxl."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="334155", end_color="334155", fill_type="solid")
    sub_fill = PatternFill(start_color="475569", end_color="475569", fill_type="solid")
    thin_border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0"),
    )

    def style_headers(ws, row=1):
        for cell in ws[row]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[row].height = 24

    def autofit(ws):
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)

    # 1. README / Legend
    ws_readme = wb.active
    ws_readme.title = "README"
    ws_readme.append(["InfraScan Inspection Report Export Workbook"])
    ws_readme["A1"].font = Font(size=14, bold=True, color="1E293B")
    ws_readme.append([])
    ws_readme.append(["Report ID", snapshot["report_id"]])
    ws_readme.append(["Inspection ID", snapshot["inspection_id"]])
    ws_readme.append(["Version", snapshot["version"]])
    ws_readme.append(["Report Status", snapshot["status"].upper()])
    ws_readme.append(["Generated At", snapshot["generated_at"]])
    ws_readme.append(["Generated By", f"{snapshot['generated_by']['name']} ({snapshot['generated_by']['email']})"])
    ws_readme.append([])
    ws_readme.append(["Mandatory Safety & Compliance Disclaimers"])
    ws_readme["A9"].font = Font(size=11, bold=True, color="991B1B")
    for d in snapshot.get("disclaimers", []):
        ws_readme.append([d])
    autofit(ws_readme)

    # 2. Summary
    ws_sum = wb.create_sheet(title="Summary")
    ws_sum.append(["Metric / Parameter", "Value"])
    style_headers(ws_sum)
    ws_sum.append(["Asset Name", snapshot["asset"]["name"]])
    ws_sum.append(["Asset Type", snapshot["asset"]["asset_type"]])
    ws_sum.append(["Material Type", snapshot["asset"]["material_type"]])
    ws_sum.append(["Address", snapshot["asset"]["address"] or "—"])
    ws_sum.append(["Total Images", snapshot["summary"]["total_images"]])
    ws_sum.append(["Analyzed Images", snapshot["summary"]["analyzed_images"]])
    ws_sum.append(["Total Detections", snapshot["summary"]["total_detections"]])
    ws_sum.append(["Worst Severity", snapshot["summary"]["worst_severity"].upper()])
    ws_sum.append(["Worst Score", snapshot["summary"]["worst_score"]])
    ws_sum.append(["Priority Suggestion", snapshot["summary"]["priority"]])
    ws_sum.append(["Fully Reviewed By Engineer", "Yes" if snapshot["summary"]["is_fully_reviewed"] else "No (Pending)"])
    autofit(ws_sum)

    # 3. Images
    ws_img = wb.create_sheet(title="Images")
    ws_img.append(["Image ID", "Filename", "Status", "Width (px)", "Height (px)", "Blur Score", "Brightness", "GPS Lat", "GPS Lon"])
    style_headers(ws_img)
    for img in snapshot.get("images", []):
        ws_img.append([
            img.get("image_id"),
            img.get("filename"),
            img.get("status"),
            img.get("width_px"),
            img.get("height_px"),
            img.get("blur_score"),
            img.get("brightness_score"),
            img.get("gps_latitude"),
            img.get("gps_longitude"),
        ])
    autofit(ws_img)

    # 4. Detections
    ws_det = wb.create_sheet(title="Detections")
    ws_det.append(["Detection ID", "Image ID", "Model ID", "Damage Class", "Confidence", "X Min", "Y Min", "X Max", "Y Max"])
    style_headers(ws_det)
    for img in snapshot.get("images", []):
        for d in img.get("detections", []):
            box = d.get("box", [0, 0, 0, 0])
            ws_det.append([
                d.get("detection_id"),
                img.get("image_id"),
                d.get("model_id"),
                d.get("damage_label") or d.get("damage_type"),
                d.get("confidence"),
                box[0], box[1], box[2], box[3],
            ])
    autofit(ws_det)

    # 5. Measurements
    ws_meas = wb.create_sheet(title="Measurements")
    ws_meas.append(["Image ID", "Crack Pixels", "Length (px)", "Avg Width (px)", "Max Width (px)", "Area (px)", "Density (%)", "mm/px Scale", "Length (mm)", "Avg Width (mm)", "Max Width (mm)", "Uncertainty (%)"])
    style_headers(ws_meas)
    for img in snapshot.get("images", []):
        m = img.get("measurements")
        if m:
            ws_meas.append([
                img.get("image_id"),
                m.get("crack_pixels"),
                m.get("length_px"),
                m.get("avg_width_px"),
                m.get("max_width_px"),
                m.get("area_px"),
                m.get("density_percent"),
                m.get("mm_per_pixel"),
                m.get("length_mm"),
                m.get("avg_width_mm"),
                m.get("max_width_mm"),
                m.get("length_mm_uncertainty"),
            ])
    autofit(ws_meas)

    # 6. Severity
    ws_sev = wb.create_sheet(title="Severity")
    ws_sev.append(["Image ID", "AI Severity", "Score", "Suggested Priority", "Review Status", "Final Severity", "Final Priority", "Reviewed By", "Comment"])
    style_headers(ws_sev)
    for img in snapshot.get("images", []):
        s = img.get("severity")
        if s:
            ws_sev.append([
                img.get("image_id"),
                s.get("severity_level"),
                s.get("score"),
                s.get("priority_suggestion"),
                s.get("review_status"),
                s.get("final_severity") or "—",
                s.get("final_priority") or "—",
                s.get("reviewed_by") or "—",
                s.get("review_comment") or "—",
            ])
    autofit(ws_sev)

    # 7. Maintenance
    ws_maint = wb.create_sheet(title="Maintenance")
    ws_maint.append(["Task ID", "Priority", "Title", "Status", "Suggested Due Date"])
    style_headers(ws_maint)
    ws_maint.append(["—", snapshot["summary"]["priority"], f"Periodic Maintenance for {snapshot['asset']['name']}", "Pending Review", "—"])
    autofit(ws_maint)

    # 8. Models
    ws_mod = wb.create_sheet(title="Models")
    ws_mod.append(["Model ID", "Model Name", "Task", "Version", "Validation / Test Metrics"])
    style_headers(ws_mod)
    for mod in snapshot.get("models", []):
        ws_mod.append([
            mod.get("model_id"),
            mod.get("model_name"),
            mod.get("task"),
            mod.get("version"),
            json.dumps(mod.get("metrics", {})),
        ])
    autofit(ws_mod)

    wb.save(output_path)
    size = os.path.getsize(output_path)
    sha256 = get_file_sha256(output_path)
    return size, sha256


def generate_pdf_report(snapshot: Dict[str, Any], output_path: Path) -> Tuple[int, str]:
    """Generate high-fidelity PDF inspection report with ReportLab."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=50,
        bottomMargin=55,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#475569"),
        spaceAfter=12,
    )
    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=14,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155"),
    )
    disclaimer_style = ParagraphStyle(
        "DisclaimerCustom",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#DC2626"),
    )

    elements = []

    # Title & Metadata
    elements.append(Paragraph(f"INFRASCAN STRUCTURAL HEALTH REPORT", title_style))
    status_label = "FINAL REPORT" if snapshot["status"] == "final" else "DRAFT — PENDING ENGINEER REVIEW"
    elements.append(Paragraph(f"Inspection #{snapshot['inspection_id']} &bull; Asset #{snapshot['asset']['asset_id']} ({snapshot['asset']['name']}) &bull; Status: <b>{status_label}</b>", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceAfter=10))

    # Executive Summary Table
    summary_data = [
        [
            Paragraph("<b>Asset Name:</b>", body_style), Paragraph(str(snapshot["asset"]["name"]), body_style),
            Paragraph("<b>Inspection Date:</b>", body_style), Paragraph(str(snapshot["inspection"]["inspection_date"]), body_style),
        ],
        [
            Paragraph("<b>Asset Type:</b>", body_style), Paragraph(f"{snapshot['asset']['asset_type']} ({snapshot['asset']['material_type']})", body_style),
            Paragraph("<b>Inspector:</b>", body_style), Paragraph(snapshot["inspection"]["inspector"]["name"] if snapshot["inspection"].get("inspector") else "Unassigned", body_style),
        ],
        [
            Paragraph("<b>Worst Severity:</b>", body_style), Paragraph(f"<font color='{'#DC2626' if snapshot['summary']['worst_severity'] in ('severe', 'critical') else '#D97706'}'><b>{snapshot['summary']['worst_severity'].upper()}</b></font>", body_style),
            Paragraph("<b>Worst Score:</b>", body_style), Paragraph(f"{snapshot['summary']['worst_score']:.1f} / 100", body_style),
        ],
        [
            Paragraph("<b>Total Images:</b>", body_style), Paragraph(str(snapshot["summary"]["total_images"]), body_style),
            Paragraph("<b>Total Detections:</b>", body_style), Paragraph(str(snapshot["summary"]["total_detections"]), body_style),
        ],
    ]
    t_summary = Table(summary_data, colWidths=[100, 166, 100, 166])
    t_summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_summary)
    elements.append(Spacer(1, 12))

    # Mandatory Disclaimers Callout Box
    disclaimer_cells = [
        [Paragraph("<b>CRITICAL NOTICE & LIMITATIONS:</b>", body_style)],
        [Paragraph("&bull; AI result for engineer review, not a final structural safety verdict.", disclaimer_style)],
        [Paragraph("&bull; No damage detected by the AI is not evidence that there is no damage.", disclaimer_style)],
        [Paragraph("&bull; Measurements without a stored perpendicular scale are in raw pixels. Millimetres are calculated only when a certified physical scale was photographed.", body_style)],
    ]
    t_disc = Table(disclaimer_cells, colWidths=[532])
    t_disc.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF2F2")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#FCA5A5")),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(t_disc)
    elements.append(Spacer(1, 14))

    # Per-Image Breakdown
    elements.append(Paragraph("DETAILED INSPECTION IMAGES & DAMAGE MEASUREMENTS", h2_style))

    for idx, img in enumerate(snapshot.get("images", []), start=1):
        img_elements = []
        img_elements.append(Paragraph(f"<b>Image #{img['image_id']}:</b> {img['filename']} ({img.get('width_px', '?')} &times; {img.get('height_px', '?')} px)", h2_style))

        # Check if local image file exists to embed thumbnail
        file_path_str = img.get("file_path")
        if file_path_str:
            p = Path(file_path_str)
            if not p.is_absolute():
                p = BASE_DIR / p
            if p.exists():
                try:
                    rl_img = RLImage(str(p), width=240, height=180)
                    img_elements.append(rl_img)
                except Exception:
                    img_elements.append(Paragraph("[Image file could not be rendered]", body_style))
            else:
                img_elements.append(Paragraph("[Image file missing on disk — catalogued as missing]", body_style))

        # Measurements table
        meas = img.get("measurements")
        if meas:
            meas_table_data = [
                ["Crack Area (px)", "Length (px)", "Avg Width (px)", "Max Width (px)", "Density (%)", "Length (mm)", "Width (mm)"],
                [
                    str(meas.get("crack_pixels") or "—"),
                    f"{meas['length_px']:.1f}" if meas.get("length_px") else "—",
                    f"{meas['avg_width_px']:.1f}" if meas.get("avg_width_px") else "—",
                    f"{meas['max_width_px']:.1f}" if meas.get("max_width_px") else "—",
                    f"{meas['density_percent']:.2f}%" if meas.get("density_percent") else "—",
                    f"{meas['length_mm']:.1f} mm" if meas.get("length_mm") else "No Scale",
                    f"{meas['avg_width_mm']:.1f} mm" if meas.get("avg_width_mm") else "No Scale",
                ],
            ]
            t_m = Table(meas_table_data, colWidths=[76, 76, 76, 76, 76, 76, 76])
            t_m.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("PADDING", (0, 0), (-1, -1), 3),
            ]))
            img_elements.append(Spacer(1, 4))
            img_elements.append(t_m)

        # Detections table
        dets = img.get("detections", [])
        if dets:
            det_rows = [["Class", "Detector Model", "AI Confidence", "Bounding Box (xmin, ymin, xmax, ymax)"]]
            for d in dets:
                det_rows.append([
                    d.get("damage_label") or d.get("damage_type"),
                    d.get("model_id"),
                    f"{d.get('confidence', 0):.1%}",
                    f"[{', '.join(f'{v:.0f}' for v in d.get('box', []))}]",
                ])
            t_d = Table(det_rows, colWidths=[120, 140, 80, 192])
            t_d.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("PADDING", (0, 0), (-1, -1), 3),
            ]))
            img_elements.append(Spacer(1, 4))
            img_elements.append(t_d)
        else:
            img_elements.append(Paragraph("No damage detected by the AI. This is not evidence that there is no damage.", body_style))

        img_elements.append(Spacer(1, 10))
        elements.append(KeepTogether(img_elements))

    # Engineer Sign-off Block
    elements.append(Spacer(1, 14))
    signoff_data = [
        [Paragraph("<b>ENGINEER REVIEW &amp; SIGN-OFF BLOCK:</b>", body_style), Paragraph("<b>VERDICT:</b>", body_style)],
        [
            Paragraph("Reviewing Structural Engineer Name: _______________________<br/>License / Registration Number: ____________________________<br/>Review Date: ___________________", body_style),
            Paragraph(f"Status: <b>{snapshot['status'].upper()}</b><br/>Sign-off Signature: _______________________<br/>Official Stamp / Seal: [ &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; ]", body_style),
        ]
    ]
    t_signoff = Table(signoff_data, colWidths=[266, 266])
    t_signoff.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94A3B8")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(KeepTogether([t_signoff]))

    # Build document
    canvas_maker = NumberedCanvas
    # Set attributes for canvas callbacks
    def on_first_page(canvas_obj, doc_obj):
        canvas_obj.report_status_text = "FINAL" if snapshot["status"] == "final" else "DRAFT"
        canvas_obj.is_draft_watermark = (snapshot["status"] == "draft")

    doc.build(elements, canvasmaker=NumberedCanvas)
    size = os.path.getsize(output_path)
    sha256 = get_file_sha256(output_path)
    return size, sha256


def create_inspection_report(
    db: Session,
    inspection_id: int,
    user: User,
    notes: Optional[str] = None,
) -> Report:
    """Generate immutable inspection report snapshot and all four file formats."""
    # 1. Build DB snapshot
    snapshot = build_inspection_snapshot(db, inspection_id, user, notes)

    # 2. Determine new version
    latest_version = (
        db.query(func.max(Report.version))
        .filter(Report.inspection_id == inspection_id)
        .scalar()
        or 0
    )
    new_version = latest_version + 1
    snapshot["version"] = new_version

    # Output directory
    report_base = settings.report_path / f"inspection_{inspection_id}_v{new_version}"
    report_base.mkdir(parents=True, exist_ok=True)

    # 3. Generate JSON snapshot
    json_path = report_base / "snapshot.json"
    json_size, json_sha256 = generate_json_file(snapshot, json_path)
    content_sha256 = json_sha256  # The content sha256 is the snapshot hash

    # 4. Create Report record
    report = Report(
        inspection_id=inspection_id,
        version=new_version,
        status=snapshot["status"],
        generated_by=user.user_id,
        generated_at=datetime.now(timezone.utc),
        content_sha256=content_sha256,
        snapshot_json_path=str(json_path),
        model_versions_json=json.dumps(snapshot["models"]),
        rules_versions_json=json.dumps({"rules_version": "v1.0"}),
        review_summary_json=json.dumps(snapshot["summary"]),
        notes=notes,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # Update snapshot report_id
    snapshot["report_id"] = report.report_id
    generate_json_file(snapshot, json_path)

    # 5. Generate other formats
    # PDF
    pdf_path = report_base / "report.pdf"
    pdf_size, pdf_sha256 = generate_pdf_report(snapshot, pdf_path)

    # CSV Bundle
    csv_zip_path, csv_size, csv_sha256 = generate_csv_bundle(snapshot, report_base)

    # Excel
    xlsx_path = report_base / "report.xlsx"
    xlsx_size, xlsx_sha256 = generate_excel_file(snapshot, xlsx_path)

    # 6. Save ReportFile entries
    files_to_save = [
        ("json", str(json_path), json_size, json_sha256),
        ("pdf", str(pdf_path), pdf_size, pdf_sha256),
        ("csv", str(csv_zip_path), csv_size, csv_sha256),
        ("xlsx", str(xlsx_path), xlsx_size, xlsx_sha256),
    ]

    for fmt, path_str, sz, sha in files_to_save:
        rf = ReportFile(
            report_id=report.report_id,
            format=fmt,
            path=path_str,
            size=sz,
            sha256=sha,
        )
        db.add(rf)
    db.commit()

    create_audit_log(
        db=db,
        action="report_generated",
        user_id=user.user_id,
        entity_type="report",
        entity_id=str(report.report_id),
    )

    return report


def export_asset_summary(
    db: Session,
    asset_id: int,
    format: str = "csv",
) -> Tuple[bytes, str, str]:
    """Export asset-level inspection and defect summary as CSV or Excel."""
    asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.asset_id == asset_id).first()
    if not asset:
        raise ValueError(f"Asset #{asset_id} not found.")

    inspections = (
        db.query(Inspection)
        .filter(Inspection.asset_id == asset_id)
        .order_by(Inspection.inspection_date.desc())
        .all()
    )

    rows = []
    for insp in inspections:
        inspector_name = (
            insp.inspector.full_name
            if (insp.inspector and insp.inspector.full_name)
            else (insp.inspector.email if insp.inspector else "Unassigned")
        )
        img_count = db.query(func.count(Image.image_id)).filter(Image.inspection_id == insp.inspection_id).scalar() or 0
        img_ids = [r[0] for r in db.query(Image.image_id).filter(Image.inspection_id == insp.inspection_id).all()]
        run_ids = [r[0] for r in db.query(AnalysisRun.run_id).filter(AnalysisRun.image_id.in_(img_ids)).all()] if img_ids else []
        det_count = (
            db.query(func.count(Detection.detection_id)).filter(Detection.run_id.in_(run_ids)).scalar()
            if run_ids
            else 0
        )
        sev = (
            db.query(InspectionSeverity)
            .filter(InspectionSeverity.inspection_id == insp.inspection_id)
            .first()
        )
        sev_cat = sev.worst_severity if sev else "none"
        sev_score = sev.worst_score if sev else 0.0
        rev_status = "pending" if (sev and sev.images_pending_review > 0) else "reviewed"

        tasks_count = (
            db.query(func.count(MaintenanceTask.task_id))
            .filter(MaintenanceTask.inspection_id == insp.inspection_id)
            .scalar()
            or 0
        )

        rows.append({
            "Inspection ID": insp.inspection_id,
            "Date": insp.inspection_date.strftime("%Y-%m-%d") if insp.inspection_date else "",
            "Inspector": inspector_name,
            "Status": insp.status,
            "Total Images": img_count,
            "Total Detections": det_count,
            "Severity Category": sev_cat,
            "Severity Score": sev_score,
            "Review Status": rev_status,
            "Maintenance Tasks": tasks_count,
        })

    safe_name = "".join(c for c in asset.name if c.isalnum() or c in ("-", "_")).rstrip()
    if format.lower() == "xlsx":
        wb = Workbook()
        ws = wb.active
        ws.title = "Asset Summary"
        ws.append(["InfraScan Asset Inspection Summary Report"])
        ws.append(["Disclaimer: AI result for engineer review, not a final structural safety verdict."])
        ws.append([])
        ws.append(["Asset ID", asset.asset_id, "Name", asset.name])
        ws.append(["Type", asset.asset_type, "Material", asset.material_type])
        ws.append(["District", asset.district or "N/A", "Importance", asset.importance_level])
        ws.append(["Department", asset.responsible_department, "Construction Year", asset.construction_year])
        ws.append(["Address", asset.address or "N/A"])
        ws.append(["Total Inspections", len(inspections)])
        ws.append([])
        headers = [
            "Inspection ID", "Date", "Inspector", "Status", "Total Images",
            "Total Detections", "Severity Category", "Severity Score", "Review Status", "Maintenance Tasks"
        ]
        ws.append(headers)
        for r in rows:
            ws.append([r[h] for h in headers])

        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=11, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf.getvalue(), f"asset_{asset_id}_{safe_name}_summary.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        out = io.StringIO()
        out.write("\ufeff")  # UTF-8 BOM
        writer = csv.writer(out)
        writer.writerow(["# InfraScan Asset Inspection Summary"])
        writer.writerow(["# Disclaimer: AI result for engineer review, not a final structural safety verdict."])
        writer.writerow(["Asset ID", asset.asset_id, "Name", sanitize_csv_cell(asset.name)])
        writer.writerow(["Type", asset.asset_type, "Material", asset.material_type])
        writer.writerow(["District", sanitize_csv_cell(asset.district or ""), "Importance", asset.importance_level])
        writer.writerow([])
        headers = [
            "Inspection ID", "Date", "Inspector", "Status", "Total Images",
            "Total Detections", "Severity Category", "Severity Score", "Review Status", "Maintenance Tasks"
        ]
        writer.writerow(headers)
        for r in rows:
            writer.writerow([sanitize_csv_cell(r[h]) for h in headers])
        return out.getvalue().encode("utf-8"), f"asset_{asset_id}_{safe_name}_summary.csv", "text/csv; charset=utf-8"


def export_portfolio_summary(
    db: Session,
    format: str = "csv",
) -> Tuple[bytes, str, str]:
    """Export complete portfolio-level summary across all infrastructure assets."""
    assets = db.query(InfrastructureAsset).order_by(InfrastructureAsset.asset_id.asc()).all()

    rows = []
    for a in assets:
        inspections = (
            db.query(Inspection)
            .filter(Inspection.asset_id == a.asset_id)
            .order_by(Inspection.inspection_date.desc())
            .all()
        )
        insp_count = len(inspections)
        latest_insp = inspections[0] if inspections else None
        latest_date = latest_insp.inspection_date.strftime("%Y-%m-%d") if latest_insp and latest_insp.inspection_date else "Never"

        insp_ids = [i.inspection_id for i in inspections]
        img_ids = [
            r[0] for r in db.query(Image.image_id).filter(Image.inspection_id.in_(insp_ids)).all()
        ] if insp_ids else []
        run_ids = [
            r[0] for r in db.query(AnalysisRun.run_id).filter(AnalysisRun.image_id.in_(img_ids)).all()
        ] if img_ids else []
        total_defects = (
            db.query(func.count(Detection.detection_id)).filter(Detection.run_id.in_(run_ids)).scalar()
            if run_ids
            else 0
        )

        latest_sev = None
        if latest_insp:
            latest_sev = (
                db.query(InspectionSeverity)
                .filter(InspectionSeverity.inspection_id == latest_insp.inspection_id)
                .first()
            )
        condition = latest_sev.worst_severity if latest_sev else "none"
        condition_score = latest_sev.worst_score if latest_sev else 0.0

        pending_tasks = (
            db.query(func.count(MaintenanceTask.task_id))
            .filter(MaintenanceTask.inspection_id.in_(insp_ids), MaintenanceTask.status != "completed")
            .scalar()
            if insp_ids
            else 0
        )

        rows.append({
            "Asset ID": a.asset_id,
            "Asset Name": a.name,
            "Type": a.asset_type,
            "Material": a.material_type,
            "District": a.district or "N/A",
            "Importance": a.importance_level,
            "Department": a.responsible_department,
            "Construction Year": a.construction_year,
            "Total Inspections": insp_count,
            "Total Defects": total_defects,
            "Latest Inspection": latest_date,
            "Latest Condition": condition,
            "Severity Score": condition_score,
            "Pending Actions": pending_tasks,
        })

    if format.lower() == "xlsx":
        wb = Workbook()
        ws = wb.active
        ws.title = "Portfolio Summary"
        ws.append(["InfraScan Structural Asset Portfolio Summary Report"])
        ws.append(["Disclaimer: AI result for engineer review, not a final structural safety verdict."])
        ws.append([f"Generated At: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"])
        ws.append([])
        headers = [
            "Asset ID", "Asset Name", "Type", "Material", "District",
            "Importance", "Department", "Construction Year", "Total Inspections",
            "Total Defects", "Latest Inspection", "Latest Condition", "Severity Score", "Pending Actions"
        ]
        ws.append(headers)
        for r in rows:
            ws.append([r[h] for h in headers])

        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=5, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf.getvalue(), "infrascan_portfolio_summary.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        out = io.StringIO()
        out.write("\ufeff")  # UTF-8 BOM
        writer = csv.writer(out)
        writer.writerow(["# InfraScan Structural Asset Portfolio Summary"])
        writer.writerow(["# Disclaimer: AI result for engineer review, not a final structural safety verdict."])
        writer.writerow([f"# Generated At: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"])
        headers = [
            "Asset ID", "Asset Name", "Type", "Material", "District",
            "Importance", "Department", "Construction Year", "Total Inspections",
            "Total Defects", "Latest Inspection", "Latest Condition", "Severity Score", "Pending Actions"
        ]
        writer.writerow(headers)
        for r in rows:
            writer.writerow([sanitize_csv_cell(r[h]) for h in headers])
        return out.getvalue().encode("utf-8"), "infrascan_portfolio_summary.csv", "text/csv; charset=utf-8"
