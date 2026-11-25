"""
Generate Milestone 3 Documentation PDF for InfraScan.
Strict adherence to facts, ReportLab styling, exact metrics, and author block.
"""

import os
import sys
from PIL import Image as PILImage
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

# Dimensions
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 54.0  # 19 mm
USABLE_WIDTH = PAGE_WIDTH - (2 * MARGIN)  # 487.27 pt

# Colors
NAVY = colors.HexColor("#1e3a8a")
SLATE = colors.HexColor("#475569")
DARK_BODY = colors.HexColor("#0f172a")
LIGHT_BG = colors.HexColor("#f8fafc")
CALLOUT_BG = colors.HexColor("#f1f5f9")
BORDER_COLOR = colors.HexColor("#e2e8f0")
WHITE = colors.HexColor("#ffffff")
EMERALD = colors.HexColor("#059669")
AMBER = colors.HexColor("#d97706")
ROSE = colors.HexColor("#e11d48")

class NumberedCanvas(canvas.Canvas):
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
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, page_count):
        self.saveState()
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 7.5)
            self.setFillColor(NAVY)
            self.drawString(MARGIN, PAGE_HEIGHT - 36, "INFRASCAN")
            self.setFont("Helvetica", 7.5)
            self.setFillColor(SLATE)
            self.drawString(MARGIN + 55, PAGE_HEIGHT - 36, "|  Milestone 3 Documentation: Advanced AI & Defect Quantification")
            self.drawRightString(PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 36, "Technical Report")
            self.setStrokeColor(BORDER_COLOR)
            self.setLineWidth(0.5)
            self.line(MARGIN, PAGE_HEIGHT - 42, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 42)
        
        # Running Footer (all pages)
        self.setStrokeColor(BORDER_COLOR)
        self.setLineWidth(0.5)
        self.line(MARGIN, 46, PAGE_WIDTH - MARGIN, 46)
        
        self.setFont("Helvetica-Oblique", 7.0)
        self.setFillColor(SLATE)
        self.drawString(MARGIN, 34, "AI result for engineer review, not a final structural safety verdict.")
        
        self.setFont("Helvetica", 7.5)
        self.drawRightString(PAGE_WIDTH - MARGIN, 34, f"Page {self._pageNumber} of {page_count}")
        
        self.restoreState()


def get_image_flowable(img_path, max_width=440, max_height=180, caption=None):
    flowables = []
    if os.path.exists(img_path):
        try:
            with PILImage.open(img_path) as im:
                orig_w, orig_h = im.size
            ratio = min(max_width / orig_w, max_height / orig_h, 1.0)
            target_w = orig_w * ratio
            target_h = orig_h * ratio
            
            flowables.append(Spacer(1, 4))
            flowables.append(Image(img_path, width=target_w, height=target_h, hAlign="CENTER"))
            if caption:
                caption_style = ParagraphStyle(
                    'CaptionStyle',
                    fontName='Helvetica-Oblique',
                    fontSize=7.5,
                    leading=9.5,
                    textColor=SLATE,
                    alignment=TA_CENTER,
                    spaceBefore=3,
                    spaceAfter=6
                )
                flowables.append(Paragraph(caption, caption_style))
            flowables.append(Spacer(1, 4))
        except Exception as e:
            print(f"Warning: could not process image {img_path}: {e}")
    else:
        print(f"Warning: image path does not exist: {img_path}")
    return flowables


def build_callout(text, style, title="MANDATORY SAFETY DISCLAIMER"):
    p_title = Paragraph(f"<b>{title}</b>", ParagraphStyle(
        'CalloutTitle', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=NAVY, spaceAfter=2
    ))
    p_body = Paragraph(text, style)
    t = Table([[ [p_title, p_body] ]], colWidths=[USABLE_WIDTH])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), CALLOUT_BG),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('LINELEFT', (0,0), (0,-1), 3.0, NAVY),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    return t


def build_milestone3_pdf(output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=NAVY,
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        fontName='Helvetica',
        fontSize=11,
        leading=14,
        textColor=SLATE,
        spaceAfter=12
    )
    h1_style = ParagraphStyle(
        'H1',
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=NAVY,
        spaceBefore=12,
        spaceAfter=5,
        keepWithNext=True
    )
    h2_style = ParagraphStyle(
        'H2',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=SLATE,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )
    body_style = ParagraphStyle(
        'Body',
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=DARK_BODY,
        spaceAfter=5,
        alignment=TA_LEFT
    )
    table_cell = ParagraphStyle(
        'TableCell',
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=DARK_BODY
    )
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=DARK_BODY
    )
    table_header = ParagraphStyle(
        'TableHeader',
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=WHITE
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("INFRASCAN TECHNICAL DOCUMENTATION", subtitle_style))
    story.append(Paragraph("Milestone 3: Advanced AI Defect Detection, Crack Geometry Quantification, and Explainability", title_style))
    story.append(Paragraph("<b>Evaluation, Mathematical Formulation, and Engineering Validation Report</b>", h2_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY, spaceAfter=8, spaceBefore=2))

    # Metadata Grid
    meta_data = [
        [
            Paragraph("<b>Project:</b> InfraScan Intelligent Infrastructure", table_cell),
            Paragraph("<b>Milestone:</b> 3 of 4 (Weeks 5-6)", table_cell),
            Paragraph("<b>Status:</b> Complete & Verified", table_cell)
        ],
        [
            Paragraph("<b>Author:</b> Shree Nidhi Pradeep", table_cell),
            Paragraph("<b>Email:</b> shreenidhipradeep2006@gmail.com", table_cell),
            Paragraph("<b>Date:</b> November 2026", table_cell)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[USABLE_WIDTH*0.4, USABLE_WIDTH*0.35, USABLE_WIDTH*0.25])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8))

    # Mandatory Honesty Disclaimer Callout
    disclaimer_text = (
        "<b>Notice to Engineers:</b> Every screen, report, and notification that conveys AI outputs carries the explicit notice: "
        "<i>\"AI result for engineer review, not a final structural safety verdict.\"</i> When no crack is detected, the system asserts: "
        "<i>\"No damage detected by the AI. This is not evidence that there is no damage.\"</i> Under no circumstances does the system "
        "render a definitive verdict of 'safe' or 'unsafe'. All physical metrics are derived from pixels and calibrated with stored uncertainty."
    )
    story.append(build_callout(disclaimer_text, body_style, "PROJECT SAFETY CONSTRAINTS & HONESTY RULES"))
    story.append(Spacer(1, 8))

    # Section 1: Executive Summary
    story.append(Paragraph("1. Executive Summary & Verification Scope", h1_style))
    story.append(Paragraph(
        "Milestone 3 advances InfraScan from baseline models to specialized defect perception, rigorous mathematical geometry "
        "quantification, multi-factor rule-based severity scoring, temporal registration, and post-hoc attribution verification. "
        "Every claim and metric in this report reflects verified on-disk weights, test artifacts, and automated test suites. "
        "No metrics have been estimated, rounded up, or evaluated post-hoc against unlabelled test splits.",
        body_style
    ))

    # Milestone 3 Verification Table
    m3_summary_data = [
        [Paragraph("Category", table_header), Paragraph("Target Feature", table_header), Paragraph("Status", table_header), Paragraph("Key Metric / Verified Evidence", table_header)],
        [Paragraph("Object Detection", table_cell_bold), Paragraph("YOLOv8s vs YOLO11s (RDD2022)", table_cell), Paragraph("IMPLEMENTED", table_cell_bold), Paragraph("YOLOv8s Winner [VAL]: mAP@50=0.4554, mAP@50:95=0.2220", table_cell)],
        [Paragraph("Multi-Class Defect", table_cell_bold), Paragraph("RT-DETR-L on CODEBRIM", table_cell), Paragraph("IMPLEMENTED", table_cell_bold), Paragraph("1,022 images, 5 classes [VAL]: mAP@50=0.4120, mAP@50:95=0.2480", table_cell)],
        [Paragraph("Classification", table_cell_bold), Paragraph("ConvNeXt / Swin Transformer", table_cell), Paragraph("NOT IMPLEMENTED", table_cell_bold), Paragraph("Not trained; ResNet-50 baseline used (docs/12_model_evaluation_report.md)", table_cell)],
        [Paragraph("Segmentation", table_cell_bold), Paragraph("SegFormer / EfficientNet", table_cell), Paragraph("NOT IMPLEMENTED", table_cell_bold), Paragraph("Not trained; ResNet-34 U-Net++ selected on Crack500", table_cell)],
        [Paragraph("Crack Geometry", table_cell_bold), Paragraph("Medial Axis Skeleton & EDT2 Width", table_cell), Paragraph("IMPLEMENTED", table_cell_bold), Paragraph("Width = 2*EDT, Orientation, Branching, Scale Tool (uncertainty +/-4.7 px)", table_cell)],
        [Paragraph("Damage Severity", table_cell_bold), Paragraph("4-Level Multi-Factor Rule Engine", table_cell), Paragraph("IMPLEMENTED", table_cell_bold), Paragraph("Factors A-F, Overrides, Kappa=0.7542, 99.08% within 1 level", table_cell)],
        [Paragraph("Historical Tracking", table_cell_bold), Paragraph("ORB+RANSAC Alignment & Rejection", table_cell), Paragraph("IMPLEMENTED", table_cell_bold), Paragraph("Growth heatmap, area delta, non-comparable flag (inliers < 15)", table_cell)],
        [Paragraph("Explainability (XAI)", table_cell_bold), Paragraph("Grad-CAM, Captum, EigenCAM", table_cell), Paragraph("IMPLEMENTED", table_cell_bold), Paragraph("Adebayo r=0.1069; Deletion ratio 2.61x impairment (docs/15_explainable_ai.md)", table_cell)],
    ]
    t_m3_sum = Table(m3_summary_data, colWidths=[80, 130, 95, 182])
    t_m3_sum.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, LIGHT_BG]),
    ]))
    story.append(t_m3_sum)
    story.append(PageBreak())

    # Section 2: Advanced Defect Detection Models
    story.append(Paragraph("2. Advanced Defect Detection Models", h1_style))
    story.append(Paragraph(
        "<b>2.1 Road Damage Detection (RDD2022 Benchmark):</b> To detect localized road distress, YOLOv8s and YOLO11s were trained "
        "and compared on a curated 8,000-image subset of the RDD2022 dataset under identical augmentation configurations. "
        "All metrics reported below are strictly <b>VALIDATION</b> metrics; the official RDD2022 test split lacks public ground-truth labels "
        "and was therefore not evaluated.",
        body_style
    ))

    rdd_table_data = [
        [Paragraph("Model Architecture", table_header), Paragraph("Split", table_header), Paragraph("Precision", table_header), Paragraph("Recall", table_header), Paragraph("mAP@50", table_header), Paragraph("mAP@50:95", table_header), Paragraph("Verdict", table_header)],
        [Paragraph("YOLOv8s (Selected)", table_cell_bold), Paragraph("VALIDATION", table_cell), Paragraph("0.5211", table_cell), Paragraph("0.4528", table_cell), Paragraph("0.4554", table_cell), Paragraph("0.2220", table_cell), Paragraph("Selected Winner", table_cell_bold)],
        [Paragraph("YOLO11s", table_cell), Paragraph("VALIDATION", table_cell), Paragraph("0.5104", table_cell), Paragraph("0.4412", table_cell), Paragraph("0.4437", table_cell), Paragraph("0.2151", table_cell), Paragraph("Subordinate mAP", table_cell)],
    ]
    t_rdd = Table(rdd_table_data, colWidths=[100, 65, 55, 55, 55, 65, 92])
    t_rdd.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, LIGHT_BG]),
    ]))
    story.append(t_rdd)
    story.append(Spacer(1, 3))
    story.append(Paragraph(
        "<i>Selection Rationale:</i> In accordance with the model selection protocol, YOLOv8s was designated as the production road defect detector "
        "by virtue of higher validation mAP@50:95 (0.2220 vs 0.2151). Note that the original project proposal target (mAP@50 >= 0.85, Recall >= 0.90) "
        "was <b>NOT REACHED</b> on the validation split due to high visual complexity, varied asphalt textures, and motion blur.",
        body_style
    ))

    # Visuals for YOLOv8s
    fig_pr = "D:\\Infosys springboards\\docs\\figures\\yolov8s_BoxPR_curve.png"
    if os.path.exists(fig_pr):
        story.extend(get_image_flowable(fig_pr, max_width=300, max_height=115, caption="Figure 1: YOLOv8s Precision-Recall Curve on RDD2022 Validation Split."))

    story.append(Paragraph(
        "<b>2.2 Multi-Class Bridge Defect Detection (CODEBRIM):</b> Real-world concrete infrastructure suffers from co-occurring damage types. "
        "We incorporated the CODEBRIM benchmark (Concrete Defect Bridge Image Dataset), comprising 1,022 processed images and 8,274 annotations "
        "spanning 5 distinct defect classes under a non-commercial academic license. An RT-DETR-L transformer-based detector was trained.",
        body_style
    ))

    codebrim_table = [
        [Paragraph("Defect Class", table_header), Paragraph("Instance Count", table_header), Paragraph("Imbalance Ratio", table_header), Paragraph("Class Role in Prioritization", table_header)],
        [Paragraph("Crack", table_cell_bold), Paragraph("3,412", table_cell), Paragraph("1.00 (Dominant)", table_cell), Paragraph("Primary structural defect; feeds geometry pipeline", table_cell)],
        [Paragraph("Spallation", table_cell_bold), Paragraph("1,845", table_cell), Paragraph("0.54", table_cell), Paragraph("Critical loss of cover concrete; triggers min High severity", table_cell)],
        [Paragraph("Efflorescence", table_cell_bold), Paragraph("1,215", table_cell), Paragraph("0.36", table_cell), Paragraph("Indicator of subsurface moisture infiltration", table_cell)],
        [Paragraph("Corrosion Stain", table_cell_bold), Paragraph("1,390", table_cell), Paragraph("0.41", table_cell), Paragraph("Secondary indicator of internal rebar oxidation", table_cell)],
        [Paragraph("Exposed Rebars", table_cell_bold), Paragraph("412", table_cell), Paragraph("0.12 (Minority)", table_cell), Paragraph("Extreme structural threat; forces Critical severity override", table_cell)],
    ]
    t_cb = Table(codebrim_table, colWidths=[90, 75, 95, 227])
    t_cb.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, LIGHT_BG]),
    ]))
    story.append(t_cb)
    story.append(Spacer(1, 3))
    story.append(Paragraph(
        "<i>CODEBRIM RT-DETR-L Performance:</i> On the validation split, RT-DETR-L achieved <b>mAP@50 = 0.4120</b> and <b>mAP@50:95 = 0.2480 [VALIDATION]</b>. "
        "The test split was held out without local labels and was not evaluated.",
        body_style
    ))

    # Architecture Disclosure
    story.append(Paragraph("<b>2.3 Architectures Not Evaluated & Transparent Rationale:</b>", h2_style))
    story.append(Paragraph(
        "In accordance with strict reporting integrity, the following architectures proposed in preliminary planning were <b>NOT EVALUATED</b>:<br/>"
        "• <b>ConvNeXt & Swin Transformer (Classification):</b> Not trained. As stated in Section 2 & 10 of <code>docs/12_model_evaluation_report.md</code>, "
        "computational resources and engineering hours were directed toward fine-grained pixel segmentation (U-Net++) and real-time detection (YOLOv8s / RT-DETR-L). "
        "ResNet-50 proved sufficient for binary presence filtering.<br/>"
        "• <b>SegFormer & EfficientNet (Segmentation):</b> Not trained. ResNet-34 U-Net and U-Net++ demonstrated stable convergence and met production inference latency targets.",
        body_style
    ))

    # Page Break for Geometry Section
    story.append(PageBreak())

    # Section 3: Semantic Segmentation & Crack Geometry Quantification
    story.append(Paragraph("3. Semantic Segmentation & Crack Geometry Quantification", h1_style))
    story.append(Paragraph(
        "<b>3.1 Dense Crack Segmentation (Crack500 & CFD Benchmark):</b> To extract crack boundaries, U-Net and U-Net++ architectures "
        "with ResNet-34 backbones were benchmarked on Crack500 and tested zero-shot on the CFD dataset.",
        body_style
    ))

    seg_table_data = [
        [Paragraph("Model", table_header), Paragraph("Split & Dataset", table_header), Paragraph("Mean Dice", table_header), Paragraph("Mean IoU", table_header), Paragraph("Pixel Dice", table_header), Paragraph("Boundary F1 (3px)", table_header)],
        [Paragraph("U-Net++ (Winner)", table_cell_bold), Paragraph("Crack500 TEST (N=1,087)", table_cell), Paragraph("0.6899 [0.680, 0.700]", table_cell), Paragraph("0.5481 [0.538, 0.558]", table_cell), Paragraph("0.7309", table_cell), Paragraph("0.4523", table_cell)],
        [Paragraph("Standard U-Net", table_cell), Paragraph("Crack500 TEST (N=1,087)", table_cell), Paragraph("0.6712", table_cell), Paragraph("0.5284", table_cell), Paragraph("0.7145", table_cell), Paragraph("0.4310", table_cell)],
        [Paragraph("U-Net++ (Zero-Shot)", table_cell_bold), Paragraph("CFD TEST (N=118)", table_cell), Paragraph("0.4533", table_cell), Paragraph("0.3109", table_cell), Paragraph("0.4912", table_cell), Paragraph("0.2840", table_cell)],
    ]
    t_seg = Table(seg_table_data, colWidths=[95, 115, 80, 75, 55, 67])
    t_seg.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, LIGHT_BG]),
    ]))
    story.append(t_seg)
    story.append(Spacer(1, 3))
    story.append(Paragraph(
        "<i>Honesty Disclosure:</i> The plan target of Dice >= 0.85 and IoU >= 0.75 was <b>NOT REACHED</b> on Crack500. "
        "The zero-shot evaluation on CFD (Mean Dice 0.4533) highlights domain shift across varying concrete aggregate textures.",
        body_style
    ))

    fig_seg_panel = "D:\\Infosys springboards\\docs\\figures\\crack500_panel_best_01.png"
    if os.path.exists(fig_seg_panel):
        story.extend(get_image_flowable(fig_seg_panel, max_width=380, max_height=110, caption="Figure 2: U-Net++ Crack Segmentation Evaluation Panel on Crack500 Test Image."))

    story.append(Paragraph("<b>3.2 Mathematical Formulation of Crack Geometry (EDT2 Pipeline):</b>", h2_style))
    story.append(Paragraph(
        "Rather than relying on black-box visual approximations, InfraScan implements a deterministic mathematical morphology pipeline "
        "in <code>backend/app/services/crack_geometry.py</code>:<br/>"
        "1. <b>Medial Axis Skeletonization:</b> Binary crack masks $M \\in \\{0, 1\\}^{H \\times W}$ are reduced to a 1-pixel wide medial centerline $S$ "
        "using Lee's topological thinning (<code>skimage.morphology.medial_axis</code>), preserving Euler characteristics.<br/>"
        "2. <b>Width Quantification via Euclidean Distance Transform (EDT):</b> For every foreground pixel $(x, y) \\in M$, the exact Euclidean distance "
        "to the nearest background pixel is computed: $D(x, y) = \\min_{(u, v) \\notin M} \\sqrt{(x-u)^2 + (y-v)^2}$. "
        "Along the skeleton path $S$, the local crack width is rigorously $W(s) = 2 \\times D(s)$. Maximum, mean, and standard deviation width are calculated.<br/>"
        "3. <b>Topology & Branch Point Extraction:</b> An 8-connectivity cross-correlation kernel evaluates neighbor count $N(s)$. "
        "Pixels with $N(s) \\ge 3$ are flagged as branch points; $N(s) = 1$ are endpoints.<br/>"
        "4. <b>Physical Scale Calibration:</b> Geometric measurements are reported in <b>pixels</b> by default. Millimeters are output "
        "<b>ONLY</b> when an operator performs reference calibration (e.g. 1.5 mm/px). Discrete grid sampling introduces an uncertainty of "
        "<b>+/-4.7 pixels (+/-7 mm)</b>.",
        body_style
    ))

    fig_geom = "D:\\Infosys springboards\\docs\\figures\\geometry_overlay_01.png"
    if os.path.exists(fig_geom):
        story.extend(get_image_flowable(fig_geom, max_width=300, max_height=100, caption="Figure 3: Extracted Medial Axis Skeleton, Width Normal Vectors, and Topological Branch Points."))

    # Page Break for Severity Section
    story.append(PageBreak())

    # Section 4: Damage Severity Assessment Engine
    story.append(Paragraph("4. Damage Severity Assessment Engine", h1_style))
    story.append(Paragraph(
        "InfraScan employs a transparent, multi-factor scoring engine defined in <code>backend/app/config/severity_rules.json</code> (v1.0). "
        "All weights are explicitly designated as <i>\"engineer-defined placeholders\"</i> pending site-specific calibration.",
        body_style
    ))

    sev_factor_table = [
        [Paragraph("Factor", table_header), Paragraph("Geometric / Defect Metric", table_header), Paragraph("Max Points", table_header), Paragraph("Physical Rationale", table_header)],
        [Paragraph("Factor A", table_cell_bold), Paragraph("Crack Density %", table_cell), Paragraph("40 pts", table_cell), Paragraph("Total damaged surface fraction over component area", table_cell)],
        [Paragraph("Factor B", table_cell_bold), Paragraph("Relative Crack Length", table_cell), Paragraph("20 pts", table_cell), Paragraph("Long continuous cracks pose higher shear failure risk", table_cell)],
        [Paragraph("Factor C", table_cell_bold), Paragraph("Branching Complexity", table_cell), Paragraph("8 pts", table_cell), Paragraph("High node count indicates multi-directional stress / fatigue", table_cell)],
        [Paragraph("Factor D", table_cell_bold), Paragraph("Damage Class Weighting", table_cell), Paragraph("40 pts", table_cell), Paragraph("Defect class penalty (spallation=30, efflorescence=15)", table_cell)],
        [Paragraph("Factor E", table_cell_bold), Paragraph("Damage Area Share %", table_cell), Paragraph("15 pts", table_cell), Paragraph("Secondary volume loss estimation", table_cell)],
        [Paragraph("Factor F", table_cell_bold), Paragraph("Calibrated Width (mm)", table_cell), Paragraph("20 pts", table_cell), Paragraph("Crack opening gauge (0 pts if uncalibrated)", table_cell)],
    ]
    t_sf = Table(sev_factor_table, colWidths=[65, 120, 65, 237])
    t_sf.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, LIGHT_BG]),
    ]))
    story.append(t_sf)
    story.append(Spacer(1, 3))
    story.append(Paragraph(
        "<b>Mandatory Safety Overrides:</b> The rule engine enforces deterministic safety floors: if any <code>exposed_bars</code> are detected, "
        "the severity is irrevocably forced to <b>Critical (Level 4)</b>. Detected extensive <code>spallation</code> forces a floor of <b>High (Level 3)</b>.<br/>"
        "<b>Rule Stability Check:</b> Evaluated across 1,087 Crack500 test images, the rule engine demonstrated <b>77.09% exact agreement</b>, "
        "<b>99.08% agreement within one level</b>, and a Quadratic Weighted Kappa of <b>kappa = 0.7542</b>.",
        body_style
    ))

    # Section 5: Historical Comparison & Temporal Alignment
    story.append(Paragraph("5. Historical Image Comparison & Crack Growth Tracking", h1_style))
    story.append(Paragraph(
        "To monitor progression across inspection cycles, InfraScan implements an automated homography alignment service "
        "(<code>backend/app/services/historical_comparison.py</code>):<br/>"
        "• <b>Feature Matching:</b> ORB (Oriented FAST and Rotated BRIEF) keypoints are extracted and matched using FLANN / BFMatcher.<br/>"
        "• <b>RANSAC Estimation:</b> A projective homography matrix $H$ is estimated with a maximum reprojection error threshold of 3.0 pixels.<br/>"
        "• <b>Non-Comparable Rejection Safeguard:</b> If fewer than 15 valid inliers are found, or if estimated scale discrepancy exceeds 2.0x, "
        "the system rejects automated alignment, sets <code>is_comparable=False</code>, and alerts the civil engineer that camera angles diverge.<br/>"
        "• <b>Growth Quantification:</b> Upon successful alignment, previous and current crack masks are overlaid to produce a difference heatmap, "
        "percentage surface expansion, and delta maximum width.",
        body_style
    ))

    # Page Break for Explainability & Limitations
    story.append(PageBreak())

    # Section 6: Explainable AI & Scientific Sanity Checks
    story.append(Paragraph("6. Explainable AI (XAI) & Attribution Sanity Checks", h1_style))
    story.append(Paragraph(
        "Deep learning feature attribution was implemented to verify that models identify genuine structural fractures rather than "
        "superficial image artifacts (e.g., shadows, oil marks, joints). In accordance with recommendations by Adebayo et al., "
        "we subjected our attribution maps to two rigorous empirical sanity checks (documented in <code>docs/15_explainable_ai.md</code>):",
        body_style
    ))

    xai_sanity_data = [
        [Paragraph("Sanity Check Test", table_header), Paragraph("Methodology", table_header), Paragraph("Observed Metric", table_header), Paragraph("Verification Outcome", table_header)],
        [
            Paragraph("Adebayo Model Parameter Randomization", table_cell_bold),
            Paragraph("Cascading layer-by-layer weight randomization of U-Net++ encoder (N=50 Crack500 validation images)", table_cell),
            Paragraph("Grad-CAM: r = 0.1069<br/>Grad-CAM++: r = -0.1685", table_cell_bold),
            Paragraph("<b>PASSED:</b> Near-zero correlation confirms attribution is sensitive to learned parameters, not an edge detector.", table_cell)
        ],
        [
            Paragraph("Pixel Deletion (Perturbation Test)", table_cell_bold),
            Paragraph("Progressive masking of top 10% highest attribution pixels vs 10% random pixels", table_cell),
            Paragraph("Targeted Delta Dice = 0.0656<br/>Random Delta Dice = 0.0252", table_cell_bold),
            Paragraph("<b>PASSED:</b> 2.61x impairment ratio demonstrates attribution maps genuinely locate defect regions.", table_cell)
        ]
    ]
    t_xai = Table(xai_sanity_data, colWidths=[100, 130, 95, 162])
    t_xai.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, LIGHT_BG]),
    ]))
    story.append(t_xai)
    story.append(Spacer(1, 4))

    # Section 7: Classification Baselines & Duplicate Audit
    story.append(Paragraph("7. Classification Baselines & Near-Duplicate Audit", h1_style))
    story.append(Paragraph(
        "<b>7.1 CCIC Benchmark & Near-Duplicate Finding:</b> On the Concrete Crack Image Dataset (CCIC), ResNet-50 achieved an exceptional "
        "test Macro F1 = <b>0.9997 [TEST, N=5,760]</b>. A subsequent perceptual hash audit (dHash distance <= 2) revealed <b>931 near-duplicates "
        "(16.16% of test set)</b> leaking from train/val splits. When evaluated exclusively on the 4,829 verified unique images, Macro F1 remained "
        "solid at <b>0.9995</b>, confirming target achievement.<br/>"
        "<b>7.2 SDNET2018 Texture Divergence:</b> On the SDNET2018 bridge deck benchmark, ResNet-50 achieved test Macro F1 = <b>0.6421 [TEST, N=8,802]</b>, "
        "failing the >= 0.85 target. Due to rough concrete grooving, the model suffered 2,429 false positives (Precision 0.3247) and overfit after Epoch 7.",
        body_style
    ))

    # Section 8: Limitations & Milestone 3 Sign-Off
    story.append(Spacer(1, 3))
    story.append(Paragraph("8. Verified Limitations & Milestone Sign-Off", h1_style))
    story.append(Paragraph(
        "1. <b>Test Splits Not Evaluated:</b> RDD2022 and CODEBRIM object detection models are verified on <b>VALIDATION</b> splits only.<br/>"
        "2. <b>Non-Trained Models:</b> ConvNeXt, Swin Transformer, SegFormer, and EfficientNet were not trained.<br/>"
        "3. <b>Physical Units:</b> Widths and lengths are in pixels; mm requires explicit scale calibration with +/-4.7 px uncertainty.<br/>"
        "4. <b>Safety Constraint:</b> All AI predictions are advisory candidates for professional engineering verification.",
        body_style
    ))
    story.append(Spacer(1, 6))

    # Formal Author Block
    author_block_data = [
        [Paragraph("<b>REPORT AUTHOR & SUBMISSION DETAILS</b>", table_header)],
        [Paragraph("<b>Submitted by:</b> Shree Nidhi Pradeep<br/><b>Email:</b> shreenidhipradeep2006@gmail.com<br/><b>Role:</b> Lead AI & Systems Engineer<br/><b>Project:</b> InfraScan Infrastructure Intelligence System", table_cell)]
    ]
    t_auth = Table(author_block_data, colWidths=[USABLE_WIDTH])
    t_auth.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('BACKGROUND', (0,1), (-1,-1), LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 1.0, NAVY),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_auth)

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Milestone 3 PDF generated successfully at: {output_path}")

if __name__ == "__main__":
    out_pdf = r"D:\Infosys springboards\docs\Milestone3_Documentation.pdf"
    build_milestone3_pdf(out_pdf)
