"""
app/services/reporting.py – Structural Inspection Multi-Format Report Generator
Generates comprehensive civil engineering inspection reports in:
1. PDF (ReportLab)
2. CSV (Python csv)
3. Excel (openpyxl)
4. JSON (structured dict)
"""

import io
import csv
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether
)
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from app.models.inspection import Inspection
from app.models.inspection_image import InspectionImage


def generate_inspection_pdf(inspection: Inspection) -> bytes:
    """
    Builds a professional PDF structural assessment report for an inspection.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1e3a8a")
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#64748b")
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=10,
        spaceAfter=5
    )
    normal_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#334155")
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#64748b")
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph("INFRASCAN STRUCTURAL HEALTH ASSESSMENT REPORT", title_style))
    story.append(Paragraph(
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | Platform: InfraScan AI v3.0 | Decision Support Standard",
        subtitle_style
    ))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2563eb"), spaceAfter=12))

    # 2. Asset & Inspection Overview Table
    asset = getattr(inspection, "asset", None)
    inspector = getattr(inspection, "inspector", None)
    inspector_name = getattr(inspector, "full_name", "Unassigned") if inspector else "Unassigned"
    
    insp_date = getattr(inspection, "inspection_date", None) or getattr(inspection, "scheduled_date", None)
    if insp_date and hasattr(insp_date, "strftime"):
        insp_date_str = insp_date.strftime("%Y-%m-%d")
    else:
        insp_date_str = str(insp_date or "N/A")

    asset_type_obj = getattr(asset, "type", None) or getattr(asset, "asset_type", None)
    asset_type_str = str(getattr(asset_type_obj, "value", asset_type_obj) or "N/A").capitalize()

    status_obj = getattr(inspection, "status", None)
    status_str = str(getattr(status_obj, "value", status_obj) or "Pending").upper()

    asset_data = [
        [
            Paragraph("<b>Asset Code:</b>", normal_style),
            Paragraph(getattr(asset, "asset_code", "N/A") if asset else "N/A", normal_style),
            Paragraph("<b>Inspection ID:</b>", normal_style),
            Paragraph(f"#{getattr(inspection, 'id', 1)}", normal_style)
        ],
        [
            Paragraph("<b>Asset Name:</b>", normal_style),
            Paragraph(getattr(asset, "name", "N/A") if asset else "N/A", normal_style),
            Paragraph("<b>Inspection Date:</b>", normal_style),
            Paragraph(insp_date_str, normal_style)
        ],
        [
            Paragraph("<b>Structure Type:</b>", normal_style),
            Paragraph(asset_type_str, normal_style),
            Paragraph("<b>Inspection Status:</b>", normal_style),
            Paragraph(status_str, normal_style)
        ],
        [
            Paragraph("<b>GPS Location:</b>", normal_style),
            Paragraph(f"{getattr(asset, 'latitude', 0.0):.4f}, {getattr(asset, 'longitude', 0.0):.4f}" if (asset and getattr(asset, 'latitude', None) is not None) else "N/A", normal_style),
            Paragraph("<b>Assigned Inspector:</b>", normal_style),
            Paragraph(inspector_name, normal_style)
        ],
        [
            Paragraph("<b>Material Type:</b>", normal_style),
            Paragraph(str(getattr(asset, "material_type", "Reinforced Concrete") or "Reinforced Concrete"), normal_style),
            Paragraph("<b>Responsible Dept:</b>", normal_style),
            Paragraph(str(getattr(asset, "responsible_department", "Civil Works") or "Civil Works"), normal_style)
        ]
    ]

    t_overview = Table(asset_data, colWidths=[95, 175, 105, 165])
    t_overview.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_overview)
    story.append(Spacer(1, 12))

    # 3. Summary Metrics
    images = getattr(inspection, "images", []) or []
    total_imgs = len(images)
    cracked_imgs = sum(1 for img in images if getattr(img, "has_crack", False) is True)
    healthy_imgs = sum(1 for img in images if getattr(img, "has_crack", False) is False)

    sev_levels = [getattr(img, "severity_level", None) for img in images if getattr(img, "severity_level", None)]
    sev_rank = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1, "None": 0}
    max_severity = max(sev_levels, key=lambda s: sev_rank.get(str(s), 0)) if sev_levels else "None"

    # Safely compute length and width numbers
    total_len_mm = 0.0
    for img in images:
        val = getattr(img, "crack_length_mm", None)
        if isinstance(val, (int, float)):
            total_len_mm += float(val)
        else:
            px_val = getattr(img, "crack_length_px", None)
            if isinstance(px_val, (int, float)):
                total_len_mm += float(px_val) * 0.2

    max_w_mm = 0.0
    for img in images:
        val = getattr(img, "max_crack_width_mm", None)
        if isinstance(val, (int, float)):
            max_w_mm = max(max_w_mm, float(val))
        else:
            px_val = getattr(img, "max_crack_width_px", None)
            if isinstance(px_val, (int, float)):
                max_w_mm = max(max_w_mm, float(px_val) * 0.2)

    sev_color = colors.HexColor("#10b981") if max_severity == "None" else colors.HexColor("#dc2626") if max_severity in ["High", "Critical"] else colors.HexColor("#f59e0b")

    story.append(Paragraph("Damage Assessment & Quantitative Metrics", section_heading))

    metrics_data = [
        [
            Paragraph("<b>Total Surfaces</b>", normal_style),
            Paragraph("<b>Defective Images</b>", normal_style),
            Paragraph("<b>Total Length</b>", normal_style),
            Paragraph("<b>Max Crack Width</b>", normal_style),
            Paragraph("<b>Max Risk Category</b>", normal_style)
        ],
        [
            Paragraph(f"<font size=12><b>{total_imgs}</b></font>", normal_style),
            Paragraph(f"<font size=12 color='#dc2626'><b>{cracked_imgs}</b></font>", normal_style),
            Paragraph(f"<font size=12><b>{total_len_mm:.1f} mm</b></font>", normal_style),
            Paragraph(f"<font size=12><b>{max_w_mm:.1f} mm</b></font>", normal_style),
            Paragraph(f"<font size=12 color='{sev_color.hexval()}'><b>{max_severity.upper()}</b></font>", normal_style)
        ]
    ]

    t_metrics = Table(metrics_data, colWidths=[105, 110, 110, 110, 105])
    t_metrics.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#ffffff")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_metrics)
    story.append(Spacer(1, 12))

    # 4. Itemized Defect Table
    story.append(Paragraph(f"Itemized Surface Inspection Findings ({total_imgs} images)", section_heading))

    table_rows = [
        [
            Paragraph("<b>#</b>", normal_style),
            Paragraph("<b>Filename</b>", normal_style),
            Paragraph("<b>Crack Type</b>", normal_style),
            Paragraph("<b>Confidence</b>", normal_style),
            Paragraph("<b>Dimensions (L / W)</b>", normal_style),
            Paragraph("<b>Density</b>", normal_style),
            Paragraph("<b>Severity</b>", normal_style)
        ]
    ]

    for idx, img in enumerate(images, start=1):
        defect_label = "<font color='#10b981'><b>Healthy</b></font>"
        if img.has_crack is True:
            ctype = img.crack_type or "Crack"
            defect_label = f"<font color='#dc2626'><b>{ctype}</b></font>"
        elif img.has_crack is None:
            defect_label = "<font color='#64748b'>Pending</font>"

        conf_val = getattr(img, "confidence_score", None)
        conf_str = f"{(float(conf_val) * 100):.1f}%" if isinstance(conf_val, (int, float)) else "N/A"
        sev_str = str(getattr(img, "severity_level", "None") or "None")

        cl_mm = getattr(img, "crack_length_mm", None)
        cl_px = getattr(img, "crack_length_px", None)
        len_val = f"{float(cl_mm):.1f}mm" if isinstance(cl_mm, (int, float)) else f"{int(cl_px) if isinstance(cl_px, (int, float)) else 0}px"

        mw_mm = getattr(img, "max_crack_width_mm", None)
        mw_px = getattr(img, "max_crack_width_px", None)
        w_val = f"{float(mw_mm):.1f}mm" if isinstance(mw_mm, (int, float)) else f"{float(mw_px):.1f}px" if isinstance(mw_px, (int, float)) else "0px"
        geom_str = f"{len_val} / {w_val}" if getattr(img, "has_crack", False) else "—"

        dens_val = getattr(img, "crack_density_pct", None)
        dens_str = f"{float(dens_val):.1f}%" if isinstance(dens_val, (int, float)) else "0%"

        fname = str(getattr(img, "original_filename", "image.jpg") or "image.jpg")
        if len(fname) > 18:
            fname = fname[:15] + "..."

        table_rows.append([
            Paragraph(str(idx), normal_style),
            Paragraph(fname, normal_style),
            Paragraph(defect_label, normal_style),
            Paragraph(conf_str, normal_style),
            Paragraph(geom_str, normal_style),
            Paragraph(dens_str, normal_style),
            Paragraph(sev_str, normal_style)
        ])

    if len(table_rows) == 1:
        table_rows.append([Paragraph("No inspection images uploaded.", normal_style), "", "", "", "", "", ""])

    t_records = Table(table_rows, colWidths=[20, 115, 135, 60, 110, 45, 55])
    t_records.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_records)
    story.append(Spacer(1, 15))

    # 5. Sign-off and Disclaimer
    signoff_data = [
        [
            Paragraph("<b>Professional Structural Engineer (PE) Review</b>", normal_style),
            Paragraph("<b>Verification Seal</b>", normal_style)
        ],
        [
            Paragraph(
                "<br/>Reviewing Engineer: ___________________________<br/>"
                "PE License & State: ___________________________<br/>"
                "Determination:  [  ] Sound / Routine    [  ] Maintenance Needed    [  ] Critical Safety Risk<br/>"
                "Comments: ___________________________________________________________",
                normal_style
            ),
            Paragraph("<br/><br/>[ Professional Engineer Seal ]", normal_style)
        ]
    ]
    t_signoff = Table(signoff_data, colWidths=[380, 160])
    t_signoff.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("ALIGN", (1, 1), (1, 1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))

    story.append(KeepTogether([
        t_signoff,
        Spacer(1, 10),
        Paragraph(
            "<b>Engineering Notice:</b> InfraScan AI crack and damage assessments represent non-destructive computer vision screening for planning purposes. Image-based assessments must not be treated as definitive structural safety evaluations without qualified physical engineering inspection.",
            disclaimer_style
        )
    ]))

    doc.build(story)
    return buffer.getvalue()


def generate_inspection_csv(inspection: Inspection) -> bytes:
    """
    Exports inspection results and itemized image defect records as CSV.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    asset = inspection.asset
    # Header metadata
    writer.writerow(["# InfraScan Inspection Report (CSV Export)"])
    writer.writerow(["Inspection ID", inspection.id])
    writer.writerow(["Asset Code", asset.asset_code if asset else "N/A"])
    writer.writerow(["Asset Name", asset.name if asset else "N/A"])
    writer.writerow(["Structure Type", asset.type.value if (asset and hasattr(asset.type, 'value')) else "N/A"])
    writer.writerow(["Inspection Date", inspection.inspection_date.isoformat() if inspection.inspection_date else "N/A"])
    writer.writerow(["Inspector", inspection.inspector.full_name if inspection.inspector else "Unassigned"])
    writer.writerow(["Status", inspection.status.value if hasattr(inspection.status, 'value') else str(inspection.status)])
    writer.writerow([])

    # Table columns
    writer.writerow([
        "Image ID",
        "Original Filename",
        "Crack Detected",
        "Confidence Score",
        "Severity Level",
        "Crack Type",
        "Length (px)",
        "Length (mm)",
        "Max Width (px)",
        "Max Width (mm)",
        "Avg Width (mm)",
        "Crack Area (mm2)",
        "Crack Density (%)",
        "Orientation (deg)",
        "Branching Nodes",
        "Quality Status",
        "Blur Score",
        "Brightness",
        "Risk Score"
    ])

    for img in inspection.images:
        writer.writerow([
            img.id,
            img.original_filename,
            "YES" if img.has_crack else "NO",
            round(img.confidence_score, 4) if img.confidence_score is not None else "",
            img.severity_level or "None",
            img.crack_type or "None",
            img.crack_length_px or 0,
            img.crack_length_mm or 0.0,
            img.max_crack_width_px or 0.0,
            img.max_crack_width_mm or 0.0,
            img.avg_crack_width_mm or 0.0,
            img.crack_area_mm2 or 0.0,
            img.crack_density_pct or 0.0,
            img.orientation_deg or 0.0,
            img.branching_points or 0,
            img.quality_status.value if hasattr(img.quality_status, 'value') else str(img.quality_status),
            img.blur_score or "",
            img.brightness or "",
            img.risk_score or 0.0
        ])

    return output.getvalue().encode("utf-8")


def generate_inspection_excel(inspection: Inspection) -> bytes:
    """
    Builds a multi-tab formatted Excel (.xlsx) workbook for the inspection.
    """
    wb = openpyxl.Workbook()

    # Tab 1: Executive Summary
    ws_summary = wb.active
    ws_summary.title = "Executive Summary"
    ws_summary.views.sheetView[0].showGridLines = True

    header_font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
    bold_font = Font(name="Calibri", size=11, bold=True)
    regular_font = Font(name="Calibri", size=11)
    title_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    th_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    th_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

    ws_summary.cell(row=1, column=1, value="InfraScan Structural Health Assessment").font = header_font
    ws_summary.cell(row=2, column=1, value=f"Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}").font = regular_font

    asset = inspection.asset
    summary_data = [
        ("Inspection ID", f"#{inspection.id}"),
        ("Asset Code", asset.asset_code if asset else "N/A"),
        ("Asset Name", asset.name if asset else "N/A"),
        ("Structure Type", asset.type.value if (asset and hasattr(asset.type, 'value')) else "N/A"),
        ("Inspection Date", inspection.inspection_date.strftime("%Y-%m-%d") if inspection.inspection_date else "N/A"),
        ("Inspector", inspection.inspector.full_name if inspection.inspector else "Unassigned"),
        ("Status", inspection.status.value if hasattr(inspection.status, 'value') else str(inspection.status)),
        ("Total Images Analyzed", len(inspection.images)),
        ("Images with Detected Defects", sum(1 for i in inspection.images if i.has_crack)),
        ("Total Crack Length (mm)", round(sum(i.crack_length_mm or 0.0 for i in inspection.images), 2)),
        ("Max Crack Width (mm)", round(max([i.max_crack_width_mm or 0.0 for i in inspection.images], default=0.0), 2))
    ]

    for r_idx, (k, v) in enumerate(summary_data, start=4):
        c1 = ws_summary.cell(row=r_idx, column=1, value=k)
        c2 = ws_summary.cell(row=r_idx, column=2, value=v)
        c1.font = bold_font
        c1.fill = title_fill
        c2.font = regular_font

    ws_summary.column_dimensions["A"].width = 28
    ws_summary.column_dimensions["B"].width = 45

    # Tab 2: Defect Quantification
    ws_defects = wb.create_sheet(title="Defect Quantification")
    ws_defects.views.sheetView[0].showGridLines = True

    columns = [
        "Image ID", "Filename", "Crack Detected", "Confidence", "Severity", "Crack Type",
        "Length (mm)", "Max Width (mm)", "Avg Width (mm)", "Area (mm2)", "Density (%)",
        "Orientation (°)", "Branching Nodes", "Quality", "Risk Score"
    ]

    for col_idx, col_name in enumerate(columns, start=1):
        cell = ws_defects.cell(row=1, column=col_idx, value=col_name)
        cell.font = th_font
        cell.fill = th_fill
        cell.alignment = Alignment(horizontal="center")

    for row_idx, img in enumerate(inspection.images, start=2):
        row_vals = [
            img.id,
            img.original_filename,
            "YES" if img.has_crack else "NO",
            f"{img.confidence_score * 100:.1f}%" if img.confidence_score is not None else "N/A",
            img.severity_level or "None",
            img.crack_type or "None",
            img.crack_length_mm or 0.0,
            img.max_crack_width_mm or 0.0,
            img.avg_crack_width_mm or 0.0,
            img.crack_area_mm2 or 0.0,
            img.crack_density_pct or 0.0,
            img.orientation_deg or 0.0,
            img.branching_points or 0,
            img.quality_status.value if hasattr(img.quality_status, 'value') else str(img.quality_status),
            img.risk_score or 0.0
        ]
        for c_idx, val in enumerate(row_vals, start=1):
            c = ws_defects.cell(row=row_idx, column=c_idx, value=val)
            c.font = regular_font

    for col in ws_defects.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws_defects.column_dimensions[col_letter].width = max(max_len + 3, 12)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def generate_inspection_json(inspection: Inspection) -> Dict[str, Any]:
    """
    Returns complete structured JSON export of the inspection record.
    """
    asset = inspection.asset
    images_list = []
    for img in inspection.images:
        images_list.append({
            "id": img.id,
            "original_filename": img.original_filename,
            "file_path": img.file_path,
            "url": f"/uploads/{img.file_path}",
            "dimensions": {"width": img.width, "height": img.height},
            "quality": {
                "status": img.quality_status.value if hasattr(img.quality_status, 'value') else str(img.quality_status),
                "blur_score": img.blur_score,
                "brightness": img.brightness
            },
            "crack_detection": {
                "has_crack": img.has_crack,
                "confidence_score": img.confidence_score,
                "severity_level": img.severity_level,
                "crack_type": img.crack_type
            },
            "crack_geometry": {
                "length_px": img.crack_length_px,
                "length_mm": img.crack_length_mm,
                "max_width_px": img.max_crack_width_px,
                "max_width_mm": img.max_crack_width_mm,
                "avg_width_mm": img.avg_crack_width_mm,
                "area_px": img.crack_area_px,
                "area_mm2": img.crack_area_mm2,
                "density_pct": img.crack_density_pct,
                "orientation_deg": img.orientation_deg,
                "branching_points": img.branching_points,
                "calibration_mm_per_px": img.calibration_mm_per_px or 0.2
            },
            "multi_class_damage": json.loads(img.damage_types) if img.damage_types else [],
            "risk_score": img.risk_score
        })

    return {
        "inspection_id": inspection.id,
        "inspection_metadata": {
            "inspection_id": inspection.id,
            "inspection_date": inspection.inspection_date.isoformat() if inspection.inspection_date else None,
            "status": inspection.status.value if hasattr(inspection.status, 'value') else str(inspection.status),
            "inspector": {
                "id": inspection.inspector_id,
                "name": inspection.inspector.full_name if inspection.inspector else "Unassigned"
            },
            "notes": inspection.notes
        },
        "asset": {
            "id": asset.id if asset else None,
            "code": asset.asset_code if asset else None,
            "name": asset.name if asset else None,
            "type": asset.type.value if (asset and hasattr(asset.type, 'value')) else None,
            "material": asset.material_type if asset else None,
            "location_gps": {
                "latitude": asset.latitude if asset else None,
                "longitude": asset.longitude if asset else None
            } if asset else None
        },
        "summary": {
            "total_images": len(inspection.images),
            "cracked_images": sum(1 for i in inspection.images if i.has_crack),
            "total_crack_length_mm": round(sum(i.crack_length_mm or 0.0 for i in inspection.images), 2),
            "max_crack_width_mm": round(max([i.max_crack_width_mm or 0.0 for i in inspection.images], default=0.0), 2)
        },
        "images": images_list,
        "disclaimer": "AI detection results are non-destructive decision support screening and do not replace physical structural engineering evaluations."
    }
