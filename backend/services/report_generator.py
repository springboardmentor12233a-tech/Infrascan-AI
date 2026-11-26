import sys, os
import os
import json
import csv
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_inspection_report_csv(inspection, result, output_csv_path: str):
    """Generates comprehensive CSV export for inspection record."""
    os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
    with open(output_csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Field", "Value"])
        writer.writerow(["Project Name", "InfraScan"])
        writer.writerow(["Report Title", "Infrastructure Damage Inspection Report"])
        writer.writerow(["Inspection ID", inspection.id])
        writer.writerow(["Timestamp", inspection.timestamp.isoformat() if inspection.timestamp else "N/A"])
        writer.writerow(["Inspector", inspection.inspector_name])
        writer.writerow(["User ID", inspection.user_id if inspection.user_id else "Unassigned/Legacy"])
        writer.writerow(["Asset Name", inspection.asset.name if inspection.asset else "Unassigned"])
        writer.writerow(["Asset Type", inspection.asset.type if inspection.asset else "N/A"])
        writer.writerow(["Location Coordinates", f"{inspection.latitude}, {inspection.longitude}" if inspection.latitude and inspection.longitude else "N/A"])
        writer.writerow(["Location Source", inspection.location_source or "None"])
        writer.writerow(["Notes", inspection.notes or "None"])
        writer.writerow(["Image Filename", inspection.image_filename or "N/A"])
        writer.writerow(["Image Dimensions", f"{result.image_width}x{result.image_height} px" if result.image_width else "N/A"])
        writer.writerow(["Crack Detected (CNN)", result.crack_detected])
        writer.writerow(["Crack Probability", result.crack_probability])
        writer.writerow(["Surface Type", result.surface_type])
        writer.writerow(["Defect Count (Crack Zones)", result.defect_count])
        writer.writerow(["Crack Area (px)", result.crack_area_px])
        writer.writerow(["Crack Area Ratio", result.crack_area_ratio])
        writer.writerow(["Crack Density (%)", result.crack_density])
        writer.writerow(["Skeleton Length (px)", result.skeleton_length_px])
        writer.writerow(["Mean Width (px)", result.mean_width_px])
        writer.writerow(["Max Width (px)", result.max_width_px])
        writer.writerow(["Orientation Angle (deg)", result.orientation_angle])
        writer.writerow(["Connected Components", result.num_components])
        writer.writerow(["Branch Points", result.num_branches])
        writer.writerow(["Severity Level", result.severity_level])
        writer.writerow(["Severity Score", result.severity_score])
        
        # Severity reasons
        reasons_str = ""
        try:
            reasons = json.loads(result.severity_reasons_json)
            reasons_str = "; ".join(reasons)
        except Exception:
            reasons_str = str(result.severity_reasons_json or "")
        writer.writerow(["Severity Rationale", reasons_str])
        
        writer.writerow(["Maintenance Priority", result.priority_level])
        writer.writerow(["Priority Score", result.priority_score])
        writer.writerow(["Priority Rationale", result.priority_rationale])
        writer.writerow(["Recommended Action", result.recommended_action])
        writer.writerow(["Urgent Engineering Review Required", result.urgent_review_required])
        writer.writerow(["Image Blur Score", result.blur_score])
        writer.writerow(["Image Brightness Mean", result.brightness_mean])
        writer.writerow(["Image Contrast Std", result.contrast_std])
        
        # Model provenance info
        model_info = ""
        try:
            m_dict = json.loads(result.model_status_json)
            model_info = f"Classifier: {m_dict.get('classification')} | Detector: {m_dict.get('detection')} | Segmentor: {m_dict.get('segmentation')}"
        except Exception:
            model_info = "InfraScan Multi-Model Pipeline (CNN, U-Net, Calibrated Vision)"
        writer.writerow(["Model Provenance & Architecture", model_info])
        writer.writerow(["Calibration Status", "Pixel-space only (is_calibrated=False). No millimeter conversion without scale reference."])
        writer.writerow(["Disclaimer", "Automated preliminary assessment. Not a certified structural safety evaluation."])
    return output_csv_path

def generate_inspection_report_pdf(inspection, result, output_pdf_path: str):
    """Generates an executive, professional multi-page PDF inspection report with imagery."""
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a')
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569')
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=10,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1e293b')
    )
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#64748b')
    )

    story = []

    # 1. Header Banner
    header_data = [
        [
            Paragraph("<b>INFRASCAN</b> â€” Civil Infrastructure AI Intelligence", title_style),
            Paragraph(f"<b>Report ID:</b> #{inspection.id}<br/><b>Date:</b> {inspection.timestamp.strftime('%Y-%m-%d %H:%M') if inspection.timestamp else 'N/A'}", subtitle_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[4.2 * inch, 3.0 * inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563eb'), spaceBefore=4, spaceAfter=8))

    # 2. Executive Metadata & Asset Details Table
    meta_data = [
        [
            Paragraph("<b>Asset Name:</b>", body_style),
            Paragraph(str(inspection.asset.name if inspection.asset else "Unassigned Asset"), body_style),
            Paragraph("<b>Inspector:</b>", body_style),
            Paragraph(str(inspection.inspector_name), body_style)
        ],
        [
            Paragraph("<b>Asset Type:</b>", body_style),
            Paragraph(str(inspection.asset.type if inspection.asset else "General Concrete"), body_style),
            Paragraph("<b>User Account:</b>", body_style),
            Paragraph(f"User #{inspection.user_id}" if inspection.user_id else "Legacy / Unassigned", body_style)
        ],
        [
            Paragraph("<b>Coordinates:</b>", body_style),
            Paragraph(f"{inspection.latitude}, {inspection.longitude}" if inspection.latitude and inspection.longitude else "None", body_style),
            Paragraph("<b>Location Source:</b>", body_style),
            Paragraph(str(inspection.location_source or "None"), body_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[1.3 * inch, 2.3 * inch, 1.3 * inch, 2.3 * inch])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8))

    # 3. Severity & Maintenance Priority Callout Box
    sev_color = colors.HexColor('#ef4444') if "Critical" in result.severity_level or "Severe" in result.severity_level else (colors.HexColor('#f59e0b') if "Moderate" in result.severity_level else colors.HexColor('#10b981'))
    
    # Extract reasons
    reasons_list = []
    try:
        reasons_list = json.loads(result.severity_reasons_json)
    except Exception:
        reasons_list = [str(result.severity_reasons_json or "")]

    callout_data = [
        [
            Paragraph(f"<b>Severity Level:</b> <font color='{sev_color.hexval()}'>{result.severity_level}</font> (Score: {result.severity_score}/100)", body_style),
            Paragraph(f"<b>Maintenance Priority:</b> <b>{result.priority_level}</b> (Score: {result.priority_score}/100)", body_style)
        ],
        [
            Paragraph(f"<b>Key Severity Factors:</b><br/>&bull; " + "<br/>&bull; ".join(reasons_list), body_style),
            Paragraph(f"<b>Action Plan:</b><br/>{result.recommended_action}", body_style)
        ]
    ]
    callout_table = Table(callout_data, colWidths=[3.6 * inch, 3.6 * inch])
    callout_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#94a3b8')),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(callout_table)
    story.append(Spacer(1, 8))

    # 4. Multi-Model AI Imagery (Side-by-side Original vs Segmentation Overlay)
    story.append(Paragraph("Inspection Imagery & Visual Defect Localization", section_heading))
    
    img_cells = []
    cell_orig = Paragraph("Original Photo Unavailable", body_style)
    cell_overlay = Paragraph("Overlay Unavailable", body_style)
    
    if inspection.original_image_path and os.path.exists(inspection.original_image_path):
        try:
            cell_orig = RLImage(inspection.original_image_path, width=3.4 * inch, height=2.3 * inch)
        except Exception:
            pass
            
    if result.overlay_image_path and os.path.exists(result.overlay_image_path):
        try:
            cell_overlay = RLImage(result.overlay_image_path, width=3.4 * inch, height=2.3 * inch)
        except Exception:
            pass

    img_table_data = [
        [Paragraph("<b>Original Surface Photograph</b>", body_style), Paragraph("<b>U-Net Crack Overlay & Boundaries</b>", body_style)],
        [cell_orig, cell_overlay]
    ]
    img_table = Table(img_table_data, colWidths=[3.6 * inch, 3.6 * inch])
    img_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('BOX', (0, 1), (0, 1), 0.5, colors.HexColor('#cbd5e1')),
        ('BOX', (1, 1), (1, 1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    story.append(img_table)
    story.append(Spacer(1, 8))

    # 5. Quantitative Geometry & Defect Metrics Table
    story.append(Paragraph("Quantitative Crack Geometry & Metrics Extraction", section_heading))
    geom_data = [
        [
            Paragraph("<b>Total Defect Area:</b>", body_style),
            Paragraph(f"{result.crack_area_px} px ({result.crack_density}% coverage)", body_style),
            Paragraph("<b>Skeleton Centerline:</b>", body_style),
            Paragraph(f"{result.skeleton_length_px} px", body_style)
        ],
        [
            Paragraph("<b>Mean Crack Width:</b>", body_style),
            Paragraph(f"{result.mean_width_px} px (Max: {result.max_width_px} px)", body_style),
            Paragraph("<b>Orientation & Branches:</b>", body_style),
            Paragraph(f"{result.orientation_angle}&deg; | {result.num_branches} branches", body_style)
        ],
        [
            Paragraph("<b>Connected Components:</b>", body_style),
            Paragraph(f"{result.num_components} discrete segments", body_style),
            Paragraph("<b>Image Quality Audit:</b>", body_style),
            Paragraph(f"Laplacian Blur: {result.blur_score} ({'Blurry' if result.is_blurry else 'Sharp'})", body_style)
        ]
    ]
    geom_table = Table(geom_data, colWidths=[1.5 * inch, 2.1 * inch, 1.5 * inch, 2.1 * inch])
    geom_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(geom_table)
    story.append(Spacer(1, 6))

    # 6. Model Provenance & Limitations Notice
    story.append(Paragraph("Model Provenance & Technical Disclaimers", section_heading))
    
    model_desc = "CNN Classifier (Concrete vs Non-Crack) | U-Net Semantic Segmentor (Pixel Defect Boundary) | YOLO11s Baseline (COCO architecture isolated from damage logic)"
    try:
        m_dict = json.loads(result.model_status_json)
        model_desc = f"â€¢ Classification: {m_dict.get('classification')}<br/>â€¢ Detection: {m_dict.get('detection')}<br/>â€¢ Segmentation: {m_dict.get('segmentation')}"
    except Exception:
        pass

    disclaimer_text = f"""
    <b>Pipeline Architecture:</b><br/>{model_desc}<br/><br/>
    <b>Physical Measurement Disclaimer:</b> In the absence of camera sensor calibration profiles, orthogonal focal distance measurements, or a known on-surface physical reference target, all geometric dimensions are reported strictly in pixels (px). Conversions to millimeters or centimeters are not assumed.<br/>
    <b>Safety Evaluation Notice:</b> Automated vision outputs provide preliminary screening indicators and do not replace certified on-site professional structural engineering inspection.
    """
    story.append(Paragraph(disclaimer_text, disclaimer_style))

    doc.build(story)
    return output_pdf_path
