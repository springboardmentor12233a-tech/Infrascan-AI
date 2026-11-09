"""
app/services/reporting.py – Structural Inspection PDF Report Generator
Generates comprehensive civil engineering inspection reports using ReportLab.
"""

import io
from datetime import datetime
from typing import List, Optional
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
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1e3a8a")
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b")
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=12,
        spaceAfter=6
    )
    normal_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155")
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#64748b")
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph("INFRASCAN STRUCTURAL HEALTH ASSESSMENT", title_style))
    story.append(Paragraph(
        f"Generated on {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')} | Automated AI Decision Support",
        subtitle_style
    ))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2563eb"), spaceAfter=15))

    # 2. Asset & Inspection Overview Table
    asset = inspection.asset
    inspector_name = inspection.inspector.full_name if inspection.inspector else "Unassigned"
    
    asset_data = [
        [
            Paragraph("<b>Asset Code:</b>", normal_style),
            Paragraph(asset.asset_code if asset else "N/A", normal_style),
            Paragraph("<b>Inspection ID:</b>", normal_style),
            Paragraph(f"#{inspection.id}", normal_style)
        ],
        [
            Paragraph("<b>Asset Name:</b>", normal_style),
            Paragraph(asset.name if asset else "N/A", normal_style),
            Paragraph("<b>Inspection Date:</b>", normal_style),
            Paragraph(inspection.scheduled_date.strftime("%Y-%m-%d") if inspection.scheduled_date else "N/A", normal_style)
        ],
        [
            Paragraph("<b>Asset Type:</b>", normal_style),
            Paragraph(asset.asset_type.value.capitalize() if asset and hasattr(asset.asset_type, 'value') else str(asset.asset_type or "N/A"), normal_style),
            Paragraph("<b>Lifecycle Status:</b>", normal_style),
            Paragraph(inspection.status.value.upper() if hasattr(inspection.status, 'value') else str(inspection.status), normal_style)
        ],
        [
            Paragraph("<b>Location / GPS:</b>", normal_style),
            Paragraph(f"{asset.latitude:.4f}, {asset.longitude:.4f}" if asset else "N/A", normal_style),
            Paragraph("<b>Inspector:</b>", normal_style),
            Paragraph(inspector_name, normal_style)
        ]
    ]

    t_overview = Table(asset_data, colWidths=[100, 160, 100, 170])
    t_overview.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t_overview)
    story.append(Spacer(1, 15))

    # 3. AI Damage Assessment Summary Metrics
    images: List[InspectionImage] = inspection.images
    total_imgs = len(images)
    cracked_imgs = sum(1 for img in images if img.has_crack is True)
    healthy_imgs = sum(1 for img in images if img.has_crack is False)
    unclassified_imgs = total_imgs - cracked_imgs - healthy_imgs
    
    # Severity order
    sev_levels = [img.severity_level for img in images if img.severity_level]
    sev_rank = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1, "None": 0}
    max_severity = "None"
    if sev_levels:
        max_severity = max(sev_levels, key=lambda s: sev_rank.get(s, 0))

    sev_color = colors.HexColor("#10b981") if max_severity == "None" else colors.HexColor("#dc2626") if max_severity in ["High", "Critical"] else colors.HexColor("#f59e0b")

    story.append(Paragraph("Damage Assessment & Defect Summary", section_heading))

    metrics_data = [
        [
            Paragraph("<b>Total Images</b>", normal_style),
            Paragraph("<b>Defects Detected</b>", normal_style),
            Paragraph("<b>Healthy Surfaces</b>", normal_style),
            Paragraph("<b>Max Severity</b>", normal_style)
        ],
        [
            Paragraph(f"<font size=13><b>{total_imgs}</b></font>", normal_style),
            Paragraph(f"<font size=13 color='#dc2626'><b>{cracked_imgs}</b></font>", normal_style),
            Paragraph(f"<font size=13 color='#10b981'><b>{healthy_imgs}</b></font>", normal_style),
            Paragraph(f"<font size=13 color='{sev_color.hexval()}'><b>{max_severity.upper()}</b></font>", normal_style)
        ]
    ]

    t_metrics = Table(metrics_data, colWidths=[130, 130, 130, 140])
    t_metrics.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#ffffff")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_metrics)
    story.append(Spacer(1, 15))

    # 4. Detailed Image Assessment Records Table
    story.append(Paragraph(f"Image Quality & Defect Records ({total_imgs})", section_heading))

    table_rows = [
        [
            Paragraph("<b>#</b>", normal_style),
            Paragraph("<b>Image File</b>", normal_style),
            Paragraph("<b>Quality</b>", normal_style),
            Paragraph("<b>Defect Status</b>", normal_style),
            Paragraph("<b>Confidence</b>", normal_style),
            Paragraph("<b>Severity</b>", normal_style)
        ]
    ]

    for idx, img in enumerate(images, start=1):
        defect_label = "<font color='#10b981'><b>Healthy</b></font>"
        if img.has_crack is True:
            defect_label = "<font color='#dc2626'><b>CRACK</b></font>"
        elif img.has_crack is None:
            defect_label = "<font color='#64748b'>Pending</font>"

        conf_str = f"{(img.confidence_score * 100):.1f}%" if img.confidence_score is not None else "N/A"
        sev_str = img.severity_level or "None"
        q_str = img.quality_status.value.upper() if hasattr(img.quality_status, 'value') else str(img.quality_status or "OK")

        fname = img.original_filename
        if len(fname) > 24:
            fname = fname[:21] + "..."

        table_rows.append([
            Paragraph(str(idx), normal_style),
            Paragraph(fname, normal_style),
            Paragraph(q_str, normal_style),
            Paragraph(defect_label, normal_style),
            Paragraph(conf_str, normal_style),
            Paragraph(sev_str, normal_style)
        ])

    if len(table_rows) == 1:
        table_rows.append([Paragraph("No inspection images uploaded.", normal_style), "", "", "", "", ""])

    t_records = Table(table_rows, colWidths=[25, 175, 75, 95, 80, 80])
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
    story.append(Spacer(1, 20))

    # 5. Engineering Sign-Off Box
    signoff_data = [
        [
            Paragraph("<b>Professional Engineer (PE) Review & Determination</b>", normal_style),
            Paragraph("<b>Official Seal / Stamp</b>", normal_style)
        ],
        [
            Paragraph("<br/><br/>Evaluator Signature: ___________________________<br/><br/>PE License Number: ___________________________<br/><br/>Determination: [  ] Safe    [  ] Action Needed    [  ] Critical Hazard", normal_style),
            Paragraph("<br/><br/><br/>[ Place PE Seal Here ]", normal_style)
        ]
    ]
    t_signoff = Table(signoff_data, colWidths=[360, 170])
    t_signoff.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("ALIGN", (1, 1), (1, 1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    
    story.append(KeepTogether([
        t_signoff,
        Spacer(1, 15),
        Paragraph(
            "<b>Engineering Disclaimer:</b> AI detection results represent automated decision-support screening and do not replace a physical structural safety evaluation. Always consult a licensed professional engineer.",
            disclaimer_style
        )
    ]))

    doc.build(story)
    return buffer.getvalue()
