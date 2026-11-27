from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def generate_inspection_pdf(
    inspection: Any,
    asset: Any,
    images: List[Any],
    assessments: List[Any],
    output_path: Path,
) -> Path:
    """
    Generate an enterprise-grade PDF structural inspection report using ReportLab.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )

    styles = getSampleStyleSheet()
    
    # Custom Palette
    NAVY = colors.HexColor("#1F4E79")
    STEEL = colors.HexColor("#2E75B6")
    SLATE = colors.HexColor("#334155")
    LIGHT_BG = colors.HexColor("#F8FAFC")
    BORDER_COLOR = colors.HexColor("#CBD5E1")

    # Typography styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=NAVY,
        alignment=1,  # Center
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748B"),
        alignment=1,
    )
    h1_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=NAVY,
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=SLATE,
    )
    bold_style = ParagraphStyle(
        "BodyBold",
        parent=body_style,
        fontName="Helvetica-Bold",
    )

    story = []

    # Title Block
    story.append(Paragraph("INFRASCAN CIVIL INFRASTRUCTURE INSPECTION REPORT", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Generated on {datetime.now(timezone.utc).strftime('%B %d, %Y - %H:%M UTC')} | Automated AI Inspection System", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=2, color=NAVY, spaceAfter=12))

    # Section 1: Asset & Inspection Profile
    story.append(Paragraph("1. Infrastructure Asset & Inspection Profile", h1_style))
    
    asset_id_str = getattr(asset, "custom_id", None) or str(getattr(asset, "asset_id", "N/A"))
    asset_name = getattr(asset, "name", "Civil Asset")
    asset_type = getattr(asset, "asset_type", "Bridge").title()
    material = getattr(asset, "material_type", "Concrete").title()
    dept = getattr(asset, "responsible_department", "Public Works")
    const_year = str(getattr(asset, "construction_year", "N/A"))
    lat = getattr(asset, "latitude", 0.0)
    lon = getattr(asset, "longitude", 0.0)
    insp_date = str(getattr(inspection, "inspection_date", datetime.now().date()))
    insp_status = getattr(inspection, "status", "Completed").upper()
    
    profile_data = [
        [Paragraph("<b>Asset ID:</b>", body_style), Paragraph(asset_id_str, body_style),
         Paragraph("<b>Asset Name:</b>", body_style), Paragraph(asset_name, body_style)],
        [Paragraph("<b>Type / Material:</b>", body_style), Paragraph(f"{asset_type} / {material}", body_style),
         Paragraph("<b>Construction Year:</b>", body_style), Paragraph(const_year, body_style)],
        [Paragraph("<b>GPS Coordinates:</b>", body_style), Paragraph(f"{lat:.4f}, {lon:.4f}", body_style),
         Paragraph("<b>Department:</b>", body_style), Paragraph(dept, body_style)],
        [Paragraph("<b>Inspection Date:</b>", body_style), Paragraph(insp_date, body_style),
         Paragraph("<b>Status:</b>", body_style), Paragraph(insp_status, bold_style)],
    ]
    t_profile = Table(profile_data, colWidths=[1.3 * inch, 2.2 * inch, 1.4 * inch, 2.1 * inch])
    t_profile.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t_profile)
    story.append(Spacer(1, 14))

    # Section 2: AI Damage Assessment Findings
    story.append(Paragraph("2. Automated Damage Findings & Geometric Evaluation", h1_style))
    
    if assessments:
        assessment_rows = [
            [
                Paragraph("<b>Defect Class</b>", bold_style),
                Paragraph("<b>Confidence</b>", bold_style),
                Paragraph("<b>Length (px)</b>", bold_style),
                Paragraph("<b>Max Width (px)</b>", bold_style),
                Paragraph("<b>Density (%)</b>", bold_style),
                Paragraph("<b>Severity</b>", bold_style),
                Paragraph("<b>Score</b>", bold_style),
            ]
        ]
        for a in assessments:
            sev = getattr(a, "severity_category", "minor").upper()
            sev_color = colors.HexColor("#DC2626") if sev in ["CRITICAL", "SEVERE"] else colors.HexColor("#D97706") if sev == "MODERATE" else colors.HexColor("#16A34A")
            assessment_rows.append([
                Paragraph(getattr(a, "defect_type", "crack").replace("_", " ").title(), body_style),
                Paragraph(f"{getattr(a, 'confidence', 0.95)*100:.1f}%", body_style),
                Paragraph(f"{getattr(a, 'crack_length_px', 0.0):.1f}", body_style),
                Paragraph(f"{getattr(a, 'max_width_px', 0.0):.1f}", body_style),
                Paragraph(f"{getattr(a, 'crack_density_pct', 0.0):.2f}%", body_style),
                Paragraph(f"<font color='{sev_color.hexval()}'><b>{sev}</b></font>", body_style),
                Paragraph(f"{getattr(a, 'severity_score', 0.0):.1f}/100", bold_style),
            ])
        t_assessments = Table(assessment_rows, colWidths=[1.5 * inch, 0.9 * inch, 0.9 * inch, 1.0 * inch, 0.9 * inch, 1.0 * inch, 0.8 * inch])
        t_assessments.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(t_assessments)
    else:
        story.append(Paragraph("<i>No active damage assessments recorded for this inspection.</i>", body_style))
    story.append(Spacer(1, 14))

    # Section 3: Engineering Maintenance Recommendations
    story.append(Paragraph("3. Maintenance Prioritization & Remediation Strategy", h1_style))
    top_score = max([getattr(a, "severity_score", 0.0) for a in assessments], default=0.0)
    top_sev = "critical" if top_score >= 85 else "severe" if top_score >= 65 else "moderate" if top_score >= 35 else "minor" if top_score > 0 else "routine"
    
    recom_data = [
        [Paragraph("<b>Overall Severity Index:</b>", body_style), Paragraph(f"<b>{top_score:.1f} / 100 ({top_sev.upper()})</b>", body_style)],
        [Paragraph("<b>Maintenance Urgency:</b>", body_style), Paragraph("Action required within 14 days" if top_score >= 65 else "Action required within 30-90 days", body_style)],
        [Paragraph("<b>Recommended Technique:</b>", body_style), Paragraph("Structural Epoxy Grouting & CFRP composite wrap" if top_score >= 65 else "Surface hydrophobic silane-siloxane moisture barrier seal", body_style)],
        [Paragraph("<b>Engineering Sign-off:</b>", body_style), Paragraph("Qualified Civil Engineer Verification Pending On-Site Review", body_style)],
    ]
    t_recom = Table(recom_data, colWidths=[2.2 * inch, 4.8 * inch])
    t_recom.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_recom)
    story.append(Spacer(1, 20))

    # Sign-off line
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_COLOR, spaceAfter=8))
    sign_data = [
        [Paragraph("<b>Lead Structural Inspector:</b> ___________________________", body_style),
         Paragraph("<b>Civil Engineer Sign-off:</b> ___________________________", body_style)],
        [Paragraph("Date: ________________________", body_style),
         Paragraph("Date: ________________________", body_style)],
    ]
    t_sign = Table(sign_data, colWidths=[3.5 * inch, 3.5 * inch])
    t_sign.setStyle(TableStyle([("PADDING", (0, 0), (-1, -1), 4)]))
    story.append(t_sign)

    doc.build(story)
    return output_path


def generate_inspection_csv(
    inspection: Any,
    asset: Any,
    images: List[Any],
    assessments: List[Any],
    output_path: Path,
) -> Path:
    """Export inspection defect data to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Inspection ID",
            "Asset ID",
            "Asset Name",
            "Asset Type",
            "Inspection Date",
            "Image ID",
            "Defect Type",
            "Confidence",
            "Length (px)",
            "Max Width (px)",
            "Crack Density (%)",
            "Severity Category",
            "Severity Score",
        ])
        insp_id = getattr(inspection, "inspection_id", "")
        asset_id = getattr(asset, "custom_id", None) or getattr(asset, "asset_id", "")
        asset_name = getattr(asset, "name", "")
        asset_type = getattr(asset, "asset_type", "")
        insp_date = str(getattr(inspection, "inspection_date", ""))

        if assessments:
            for a in assessments:
                writer.writerow([
                    insp_id,
                    asset_id,
                    asset_name,
                    asset_type,
                    insp_date,
                    getattr(a, "image_id", ""),
                    getattr(a, "defect_type", ""),
                    getattr(a, "confidence", ""),
                    getattr(a, "crack_length_px", ""),
                    getattr(a, "max_width_px", ""),
                    getattr(a, "crack_density_pct", ""),
                    getattr(a, "severity_category", ""),
                    getattr(a, "severity_score", ""),
                ])
        else:
            writer.writerow([insp_id, asset_id, asset_name, asset_type, insp_date, "", "no_damage", 1.0, 0, 0, 0, "no_damage", 0])
    return output_path


def generate_inspection_json(
    inspection: Any,
    asset: Any,
    images: List[Any],
    assessments: List[Any],
    output_path: Path,
) -> Path:
    """Export inspection metadata and findings to structured JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "inspection": {
            "inspection_id": getattr(inspection, "inspection_id", None),
            "inspection_date": str(getattr(inspection, "inspection_date", "")),
            "status": getattr(inspection, "status", None),
        },
        "asset": {
            "asset_id": getattr(asset, "custom_id", None) or getattr(asset, "asset_id", None),
            "name": getattr(asset, "name", None),
            "asset_type": getattr(asset, "asset_type", None),
            "material_type": getattr(asset, "material_type", None),
            "latitude": getattr(asset, "latitude", None),
            "longitude": getattr(asset, "longitude", None),
        },
        "total_images": len(images),
        "assessments": [
            {
                "assessment_id": getattr(a, "assessment_id", None),
                "image_id": getattr(a, "image_id", None),
                "defect_type": getattr(a, "defect_type", None),
                "confidence": getattr(a, "confidence", None),
                "crack_length_px": getattr(a, "crack_length_px", None),
                "max_width_px": getattr(a, "max_width_px", None),
                "crack_density_pct": getattr(a, "crack_density_pct", None),
                "severity_category": getattr(a, "severity_category", None),
                "severity_score": getattr(a, "severity_score", None),
            }
            for a in assessments
        ],
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return output_path
