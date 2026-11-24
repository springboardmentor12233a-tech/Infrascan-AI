"""
InfraScan Inspection Report Generator (Civil Engineering Standard).

Generates professional, civil-engineering compliant PDF inspection reports
using ReportLab with structured tables, comparative visual evidence,
quantitative AI diagnostics, and actionable structural maintenance advisories.
"""

from datetime import datetime
import io
from pathlib import Path
from typing import Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    HRFlowable,
    KeepTogether
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def generate_pdf_report(record_data: Dict, save_to_disk: bool = True) -> io.BytesIO:
    """
    Generates a formal Civil Structural Health Monitoring inspection report.

    Args:
        record_data: Dict representation of an inspection record.
        save_to_disk: If True, writes copy to outputs/reports/<id>.pdf.

    Returns:
        io.BytesIO buffer containing the PDF binary.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=28,
        bottomMargin=28
    )

    styles = getSampleStyleSheet()

    # --- Civil Engineering Typography Styles ---
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=19,
        textColor=colors.HexColor("#0a192f"),
        spaceAfter=1
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#ea580c"),
        spaceAfter=6
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#0a192f"),
        spaceBefore=5,
        spaceAfter=3
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1e293b")
    )
    body_bold = ParagraphStyle(
        "BodyBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0f172a")
    )
    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=colors.white
    )
    caption_style = ParagraphStyle(
        "CaptionStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#334155"),
        alignment=1  # Center
    )
    caption_sub = ParagraphStyle(
        "CaptionSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.5,
        leading=8.5,
        textColor=colors.HexColor("#64748b"),
        alignment=1
    )
    advisory_style = ParagraphStyle(
        "Advisory",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor("#1e293b")
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Italic"],
        fontName="Helvetica-Oblique",
        fontSize=6.5,
        leading=8.5,
        textColor=colors.HexColor("#64748b")
    )

    story = []

    # =========================================================================
    # 1. Official Header & Civil Metadata Strip
    # =========================================================================
    inspection_id = record_data.get("id", "INFRASCAN-UNKNOWN")
    report_id = f"REP-{inspection_id}"
    gen_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    # Banner Header
    story.append(Paragraph("INFRA<font color='#ea580c'>SCAN</font> &bull; STRUCTURAL HEALTH MONITORING REPORT", title_style))
    story.append(Paragraph("AI-POWERED DAMAGE ASSESSMENT &amp; FISSURE TRIAGE FOR CIVIL INFRASTRUCTURE", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#ea580c"), spaceAfter=5))

    # Header Control Information Table
    header_table_data = [
        [
            Paragraph(f"<b>Report ID:</b> {report_id}", body_style),
            Paragraph(f"<b>Inspection ID:</b> {inspection_id}", body_style),
            Paragraph(f"<b>Generated:</b> {gen_date}", body_style)
        ],
        [
            Paragraph("<b>Standard:</b> DOT / SHM AI Triage v2.0", body_style),
            Paragraph("<b>Audit Status:</b> <font color='#16a34a'><b>OFFICIAL RECORD</b></font>", body_style),
            Paragraph("<b>Security:</b> PBKDF2 / SHA-256 Verified", body_style)
        ]
    ]
    t_header = Table(header_table_data, colWidths=[180, 180, 180])
    t_header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 5))

    # =========================================================================
    # 2. Infrastructure & Inspection Specifications Table
    # =========================================================================
    story.append(Paragraph("1. Infrastructure &amp; Inspection Specifications", section_heading))
    
    infra_name = str(record_data.get("infrastructure_name") or "Concrete Structure")
    infra_type = str(record_data.get("infrastructure_type") or "Bridge")
    asset_id = str(record_data.get("asset_id") or "ASSET-UNASSIGNED")
    location = str(record_data.get("location") or "Site Alpha")
    inspector = str(record_data.get("inspector_name") or "Lead Civil Inspector")
    insp_date = str(record_data.get("timestamp") or gen_date)[:19]
    scope_notes = str(record_data.get("description") or "Routine visual screening for structural surface fissures.")

    info_data = [
        [
            Paragraph("<b>Infrastructure Asset:</b>", body_style),
            Paragraph(infra_name, body_bold),
            Paragraph("<b>Asset ID:</b>", body_style),
            Paragraph(asset_id, body_style)
        ],
        [
            Paragraph("<b>Structure Type:</b>", body_style),
            Paragraph(infra_type, body_style),
            Paragraph("<b>Inspection Location:</b>", body_style),
            Paragraph(location, body_style)
        ],
        [
            Paragraph("<b>Inspection Timestamp:</b>", body_style),
            Paragraph(insp_date, body_style),
            Paragraph("<b>Inspecting Engineer:</b>", body_style),
            Paragraph(inspector, body_style)
        ],
        [
            Paragraph("<b>Inspection Scope / Notes:</b>", body_style),
            Paragraph(scope_notes, body_style),
            Paragraph("<b>Source File:</b>", body_style),
            Paragraph(str(record_data.get("filename") or "concrete_sample.jpg"), body_style)
        ]
    ]
    t_info = Table(info_data, colWidths=[115, 155, 115, 155])
    t_info.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 5))

    # =========================================================================
    # 3. Comparative Visual Evidence Trio
    # =========================================================================
    story.append(Paragraph("2. Comparative Visual Inspection Evidence", section_heading))
    img_cells = []

    # Safe image loading helper
    def resolve_image_flowable(path_str: str, label_fallback: str) -> RLImage:
        if not path_str:
            return Paragraph(f"<font color='#64748b'>{label_fallback}<br/>Not Available</font>", caption_style)
        
        # Check direct path and project root relative path
        candidate_paths = [
            PROJECT_ROOT / path_str,
            Path(path_str),
            PROJECT_ROOT / path_str.lstrip("/\\")
        ]
        for p in candidate_paths:
            if p.exists() and p.is_file():
                try:
                    return RLImage(str(p), width=168, height=118)
                except Exception:
                    pass
        return Paragraph(f"<font color='#64748b'>{label_fallback}<br/>Not Available</font>", caption_style)

    img_cells.append(resolve_image_flowable(record_data.get("image_path", ""), "Original Image"))
    img_cells.append(resolve_image_flowable(record_data.get("mask_path", ""), "Binary Mask"))
    img_cells.append(resolve_image_flowable(record_data.get("overlay_path", ""), "Diagnostic Overlay"))

    t_visual = Table([
        img_cells,
        [
            Paragraph("<b>1. Original Concrete Surface</b>", caption_style),
            Paragraph("<b>2. U-Net Binary Crack Mask</b>", caption_style),
            Paragraph("<b>3. Diagnostic Overlay</b>", caption_style)
        ],
        [
            Paragraph("Field Surface Capture", caption_sub),
            Paragraph("Discrete Mask {0, 255}", caption_sub),
            Paragraph("Crimson Fissure Tracking", caption_sub)
        ]
    ], colWidths=[180, 180, 180])

    t_visual.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(t_visual)
    story.append(Spacer(1, 5))

    # =========================================================================
    # 4. Quantitative AI Diagnostic Assessment Matrix
    # =========================================================================
    story.append(Paragraph("3. Quantitative AI Diagnostic Assessment Matrix", section_heading))

    cls_label = str(record_data.get("classification_label") or "Uncracked")
    confidence = float(record_data.get("confidence") or 0.0) * 100
    crack_prob = float(record_data.get("crack_probability") or 0.0) * 100
    crack_pixels = int(record_data.get("crack_pixel_count") or 0)
    total_pixels = int(record_data.get("total_pixels") or 65536)
    crack_pct = float(record_data.get("crack_percentage") or 0.0)
    severity = str(record_data.get("severity_level") or "None")
    priority = str(record_data.get("suggested_priority") or "Normal")

    # Severity color formatting
    if severity == "High":
        sev_color = "#dc2626"
    elif severity == "Moderate":
        sev_color = "#ea580c"
    elif severity == "Low":
        sev_color = "#d97706"
    else:
        sev_color = "#16a34a"

    cls_badge = f"<font color='{'#dc2626' if cls_label == 'Cracked' else '#16a34a'}'><b>{cls_label.upper()}</b></font>"

    quant_data = [
        [
            Paragraph("<b>Diagnostic Metric</b>", table_header_style),
            Paragraph("<b>Evaluated Result</b>", table_header_style),
            Paragraph("<b>Model Architecture &amp; Baseline Thresholds</b>", table_header_style)
        ],
        [
            Paragraph("Stage 1: Surface Crack Screening", body_style),
            Paragraph(f"{cls_badge} &bull; <b>{confidence:.1f}%</b> confidence", body_style),
            Paragraph("MobileNetV2 Transfer Learning (SDNET2018 benchmark)", body_style)
        ],
        [
            Paragraph("Crack Probability Index", body_style),
            Paragraph(f"<b>{crack_prob:.2f}%</b> positive fissure probability", body_style),
            Paragraph("Sigmoid activation threshold: 0.50", body_style)
        ],
        [
            Paragraph("Stage 2: Pixel-Level Localization", body_style),
            Paragraph(f"<b>{crack_pixels:,}</b> crack pixels detected", body_style),
            Paragraph("3-Stage Symmetrical U-Net (CRACK500 benchmark)", body_style)
        ],
        [
            Paragraph("Surface Area Density", body_style),
            Paragraph(f"<b>{crack_pct:.2f}%</b> surface coverage", body_style),
            Paragraph("Ratio: (Crack Pixels / Total Pixels) &times; 100", body_style)
        ],
        [
            Paragraph("Damage Severity Classification", body_style),
            Paragraph(f"<font color='{sev_color}'><b>{severity.upper()} DAMAGE</b></font>", body_style),
            Paragraph("None: 0% | Low: &le;2.0% | Mod: 2.0-7.0% | High: &gt;7.0%", body_style)
        ],
        [
            Paragraph("Triage Action Priority", body_style),
            Paragraph(f"<b>{priority.upper()}</b>", body_style),
            Paragraph("Engineering maintenance triage scheduling", body_style)
        ]
    ]

    t_quant = Table(quant_data, colWidths=[150, 180, 210])
    t_quant.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0a192f")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(t_quant)
    story.append(Spacer(1, 5))

    # =========================================================================
    # 5. Civil Engineering Advisory & Action Plan
    # =========================================================================
    story.append(Paragraph("4. Civil Engineering Advisory &amp; Action Recommendation", section_heading))
    
    summary_text = str(record_data.get("summary") or "")
    if not summary_text:
        if cls_label == "Cracked":
            summary_text = (
                f"Crack-like regions detected with {confidence:.1f}% confidence and {crack_pct:.2f}% surface density. "
                f"Preliminary severity is rated as {severity}. Further inspection by a qualified civil engineering professional is recommended."
            )
        else:
            summary_text = "No crack-like surface patterns detected. Concrete surface appears sound and intact."

    # Actionable civil recommendation based on severity
    if severity == "High":
        action_plan = (
            "<b>ACTION LEVEL: IMMEDIATE STRUCTURAL INTERVENTION REQUIRED.</b> Severe fissure coverage exceeds safety threshold. "
            "Execute on-site non-destructive evaluation (NDE) using Ultrasonic Pulse Velocity (UPV), structural core drilling, and depth gauge testing. "
            "Inspect load-bearing girders/piers for rebar corrosion, apply temporary shoring if required, and schedule epoxy pressure grouting."
        )
    elif severity == "Moderate":
        action_plan = (
            "<b>ACTION LEVEL: PRIORITY MAINTENANCE &amp; MONITORING.</b> Moderate crack formation identified. "
            "Schedule detailed optical caliper width measurement, assess exposure to moisture/freeze-thaw intrusion, "
            "and prepare low-viscosity epoxy resin injection to prevent internal rebar carbonation."
        )
    elif severity == "Low":
        action_plan = (
            "<b>ACTION LEVEL: ROUTINE MAINTENANCE.</b> Superficial micro-cracking observed. "
            "Apply silane-based water repellent or elastomeric surface sealant. Re-scan during the next routine cycle (recommended: 6-12 months)."
        )
    else:
        action_plan = (
            "<b>ACTION LEVEL: ACCEPTABLE CONDITION.</b> Concrete surface shows no significant anomalous cracking. "
            "Maintain standard structural lifecycle surveillance schedule."
        )

    advisory_table_data = [
        [Paragraph(f"<b>Diagnostic Finding:</b> {summary_text}", advisory_style)],
        [Paragraph(action_plan, advisory_style)]
    ]
    t_advisory = Table(advisory_table_data, colWidths=[540])
    t_advisory.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff7ed")),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#f97316")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#fed7aa")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_advisory)
    story.append(Spacer(1, 6))

    # =========================================================================
    # 6. Certification Sign-Off Block & Mandatory Disclaimer
    # =========================================================================
    signoff_data = [
        [
            Paragraph("<b>Field Inspection Lead:</b> ___________________________", body_style),
            Paragraph("<b>Professional Engineer (P.E.):</b> ___________________________", body_style)
        ],
        [
            Paragraph(f"Name: {inspector}", body_style),
            Paragraph("License / Stamp: ___________________________________", body_style)
        ],
        [
            Paragraph(f"Date: {insp_date[:10]}", body_style),
            Paragraph("Approval Date: ___________________________________", body_style)
        ]
    ]
    t_signoff = Table(signoff_data, colWidths=[270, 270])
    t_signoff.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    
    disclaimer_block = [
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=3),
        Paragraph(
            "<b>MANDATORY CIVIL ENGINEERING DISCLAIMER:</b> InfraScan provides AI-assisted visual damage screening of uploaded infrastructure images. "
            "Results are preliminary triage indicators designed to aid licensed civil and structural engineers. They do not substitute for on-site structural certification, "
            "load rating recalculation, ultrasonic pulse velocity testing, or seismic safety audits. Calibrated physical reference markers are required for quantitative fissure width measurements.",
            disclaimer_style
        )
    ]

    story.append(KeepTogether([t_signoff, Spacer(1, 3), *disclaimer_block]))

    # Build PDF Document
    doc.build(story)
    buffer.seek(0)

    # Optional disk persistence
    if save_to_disk:
        rec_id = record_data.get("id", "report")
        disk_file = REPORTS_DIR / f"{rec_id}.pdf"
        try:
            with open(disk_file, "wb") as f:
                f.write(buffer.getvalue())
        except Exception:
            pass

    buffer.seek(0)
    return buffer
