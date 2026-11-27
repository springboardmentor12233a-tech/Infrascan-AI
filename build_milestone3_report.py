import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH_1 = os.path.join(SCRIPT_DIR, "InfraScan_Milestone_3_Report.docx")
OUTPUT_PATH_2 = os.path.join(PROJECT_ROOT, "InfraScan_Milestone_3_Report.docx")
REPORTS_DIR = os.path.join(SCRIPT_DIR, "docs", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)
OUTPUT_PATH_3 = os.path.join(REPORTS_DIR, "InfraScan_Milestone_3_Report.docx")

def build_report():
    doc = Document()

    # 1. Page Margins (standard Calibri template: top/bottom 0.65", left/right 0.75")
    for sec in doc.sections:
        sec.top_margin = Inches(0.65)
        sec.bottom_margin = Inches(0.65)
        sec.left_margin = Inches(0.75)
        sec.right_margin = Inches(0.75)
        sec.header_distance = Inches(0.4)
        sec.footer_distance = Inches(0.4)

    # Color Palette matching Milestones 1 & 2
    NAVY = RGBColor(0x1F, 0x4E, 0x79)
    DARK_BLUE = RGBColor(0x2E, 0x75, 0xB6)
    CHARCOAL = RGBColor(0x26, 0x26, 0x26)
    MUTED = RGBColor(0x59, 0x59, 0x59)

    # Configure Normal Style
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(10.5)
    normal_style.font.color.rgb = CHARCOAL

    # Header / Title Block
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(2)
    r_title = p_title.add_run("INFRASCAN")
    r_title.bold = True
    r_title.font.size = Pt(27)
    r_title.font.color.rgb = NAVY

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(4)
    r_sub = p_sub.add_run("AI-Powered Crack & Damage Assessment\nfor Civil Infrastructure")
    r_sub.bold = True
    r_sub.font.size = Pt(16)
    r_sub.font.color.rgb = CHARCOAL

    p_mile = doc.add_paragraph()
    p_mile.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_mile.paragraph_format.space_before = Pt(0)
    p_mile.paragraph_format.space_after = Pt(2)
    r_mile = p_mile.add_run("MILESTONE 3 REPORT  |  Weeks 5–6")
    r_mile.bold = True
    r_mile.font.size = Pt(11)
    r_mile.font.color.rgb = NAVY

    p_prep = doc.add_paragraph()
    p_prep.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_prep.paragraph_format.space_before = Pt(0)
    p_prep.paragraph_format.space_after = Pt(14)
    r_prep = p_prep.add_run("Damage Assessment, Advanced AI & Analytics Engine  •  Technical Implementation & Validation Report")
    r_prep.font.size = Pt(10)
    r_prep.font.color.rgb = MUTED

    def add_h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.bold = True
        r.font.name = 'Calibri'
        r.font.size = Pt(14)
        r.font.color.rgb = NAVY
        return p

    def add_h2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.bold = True
        r.font.name = 'Calibri'
        r.font.size = Pt(12)
        r.font.color.rgb = DARK_BLUE
        return p

    def add_p(text, bold_prefix=None):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            r_b = p.add_run(bold_prefix)
            r_b.bold = True
        p.add_run(text)
        return p

    def add_bullet(text, bold_prefix=None):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(2.5)
        p.paragraph_format.line_spacing = 1.12
        if bold_prefix:
            r_b = p.add_run(bold_prefix)
            r_b.bold = True
        p.add_run(text)
        return p

    # Section 1
    add_h1("1. Executive Summary & Milestone 3 Scope")
    add_p(
        "Milestone 3 of the InfraScan project marks the transition from foundational crack classification and preliminary segmentation to a fully integrated, multi-model AI analytics and damage assessment engine. While Milestones 1 and 2 established data ingestion, quality validation, binary crack classification, and initial U-Net masking, civil infrastructure asset management demands quantitative engineering indicators, multi-class surface defect detection, explainability, temporal progression modeling, and automated maintenance prioritization."
    )
    add_p(
        "During Weeks 5 and 6, the engineering team designed and deployed six core analytical modules:",
        bold_prefix="Core Accomplishments: "
    )
    add_bullet("Multi-class surface defect detection distinguishing cracks, potholes, spalling, exposed rebar, corrosion, and water staining with bounding box localization.", bold_prefix="Multi-Class AI Detection: ")
    add_bullet("Pixel-level crack mask extraction and advanced morphological geometry quantification (Zhang-Suen skeletonization, Euclidean distance transform, length, maximum/average width, density, and orientation).", bold_prefix="Crack Geometry Matrix: ")
    add_bullet("A mathematical, quantitative Damage Severity Index (0–100) combining structural defect type, maximum crack width, total length, crack density, and asset criticality tiers.", bold_prefix="Severity Scoring Engine: ")
    add_bullet("Explainable AI (XAI) using Grad-CAM saliency attention heatmaps, providing transparent visual justification for model inferences to civil engineers.", bold_prefix="Explainable AI (Grad-CAM): ")
    add_bullet("Historical inspection comparison quantifying delta crack length, delta width, growth rate %, and deterioration trend categorization (stable, minor, moderate, accelerated).", bold_prefix="Multi-Temporal Progression: ")
    add_bullet("Automated maintenance prioritization assigning urgency timeframes, cost estimation tiers, and standard engineering remediation techniques.", bold_prefix="Maintenance Engine: ")

    # Section 2
    add_h1("2. Multi-Class Surface Defect Detection Architecture")
    add_p(
        "Civil structures suffer from heterogeneous degradation modes beyond simple longitudinal cracks. The InfraScan multi-class detection pipeline identifies six distinct surface defect categories:"
    )
    add_bullet("Longitudinal, transverse, and alligator fracture patterns threatening structural integrity.", bold_prefix="1. Concrete Cracks: ")
    add_bullet("Surface depressions and localized cavity failures prevalent on asphalt bridge decks and highway overpasses.", bold_prefix="2. Potholes: ")
    add_bullet("Flaking and delamination of concrete surface layers exposing internal aggregate, caused by freeze-thaw cycles or impact.", bold_prefix="3. Concrete Spalling: ")
    add_bullet("Structural reinforcement steel exposed due to deep spalling, requiring immediate passivation and concrete jacket retrofitting.", bold_prefix="4. Exposed Rebar: ")
    add_bullet("Iron oxide expansion staining on steel-reinforced interfaces indicating moisture ingress and accelerated section loss.", bold_prefix="5. Corrosion / Rust: ")
    add_bullet("Efflorescence and persistent moisture seepage compromising structural waterproofing.", bold_prefix="6. Water Staining: ")
    add_p(
        "The backend service (app/ai/damage_detection.py) implements YOLOv8 multi-class object detection coupled with morphological bounding box refinement, yielding class confidence scores, normalized coordinates [x1, y1, x2, y2], and defect surface area proportions."
    )

    # Section 3
    add_h1("3. Morphological Crack Geometry Extraction")
    add_p(
        "Accurate civil engineering assessment requires physical geometric dimensions rather than raw pixel counts. The crack geometry module (app/ai/geometry.py) processes binary segmentation masks through a multi-stage morphological algorithm:"
    )
    add_bullet("Reduces binary crack masks to a 1-pixel-wide medial centerline, enabling topological path tracing and branch elimination.", bold_prefix="Zhang-Suen Skeletonization: ")
    add_bullet("Computes the exact distance from each crack pixel to the nearest background pixel, where the maximum distance value on the skeleton corresponds to half the maximum crack width (R_max). Maximum width is therefore calculated as 2 * R_max.", bold_prefix="Euclidean Distance Transform: ")
    add_bullet("Calculates the total count of skeleton pixels multiplied by the optical calibration scale factor (mm/pixel) to yield true metric length in millimeters.", bold_prefix="Crack Length Measurement: ")
    add_bullet("Evaluates the ratio of segmented crack area to the total structural surface area, expressed as a percentage.", bold_prefix="Crack Density Percentage: ")
    add_bullet("Determines principal crack direction via image second moments and PCA eigenvectors, distinguishing structural shear cracks (approx 45 degrees) from flexural cracks (approx 90 degrees).", bold_prefix="Crack Orientation: ")

    # Section 4
    add_h1("4. Quantitative Damage Severity Index (0–100)")
    add_p(
        "To eliminate subjective inspector bias, InfraScan synthesizes morphological and defect properties into a deterministic 0–100 Damage Severity Index (DSI). The formulation incorporates:"
    )
    add_p(
        "DSI = clamp(Base_Defect_Score + W_width * Score_width + W_length * Score_length + W_density * Score_density + Asset_Criticality_Bonus, 0, 100)"
    )
    add_p("The resulting score maps directly to five standardized civil infrastructure maintenance categories:")
    add_bullet("DSI 0–19: Sound concrete structure; no structural remediation required; continue scheduled periodic surveillance.", bold_prefix="Tier 1: No Damage / Negligible: ")
    add_bullet("DSI 20–39: Hairline hairline cracking (<0.2 mm); cosmetic sealant or surface treatment; routine annual monitoring.", bold_prefix="Tier 2: Minor Damage: ")
    add_bullet("DSI 40–59: Structural crack widths between 0.3 mm and 1.5 mm; targeted epoxy injection or polymer grouting recommended within 90 days.", bold_prefix="Tier 3: Moderate Damage: ")
    add_bullet("DSI 60–79: Crack widths between 1.5 mm and 5.0 mm, spalling, or visible moisture ingress; high-priority structural repair within 30 days.", bold_prefix="Tier 4: Severe Damage: ")
    add_bullet("DSI 80–100: Exposed rebar, crack widths exceeding 5.0 mm, or severe spalling on high-criticality assets; immediate engineering review, load restriction, and emergency shoring.", bold_prefix="Tier 5: Critical / Urgent: ")

    # Section 5
    add_h1("5. Explainable AI: Grad-CAM Saliency Attention")
    add_p(
        "A critical barrier to deploying deep learning in civil engineering is the 'black-box' nature of neural networks. Milestone 3 implements Gradient-weighted Class Activation Mapping (Grad-CAM in app/ai/explainability.py). The module captures gradient signals flowing into the final convolutional feature maps, weights them by activation importance, and computes a 2D attention heatmap."
    )
    add_p(
        "The raw heatmap is normalized, passed through an OpenCV JET colormap, and blended as a 50% semi-transparent overlay onto the original high-resolution photo. This allows structural engineers to visually verify that model predictions are genuinely anchored to surface fissures and delaminations rather than background noise, lighting artifacts, or camera shadows."
    )

    # Section 6
    add_h1("6. Multi-Temporal Damage Progression Tracking")
    add_p(
        "Static assessments fail to capture whether a crack is dormant or actively propagating. The progression analysis engine (app/ai/progression.py) correlates inspection records across time for any given infrastructure asset:"
    )
    add_bullet("Quantifies absolute elongation (Delta L) and widening (Delta W) between successive inspection dates.", bold_prefix="Delta Metrics: ")
    add_bullet("Calculates normalized annual or monthly propagation percentage relative to baseline crack length.", bold_prefix="Growth Rate (%): ")
    add_bullet("Classifies structural behavior into four distinct trends: 'Stable' (<5% change), 'Minor Progression' (5–15%), 'Moderate Deterioration' (15–30%), and 'Accelerated Propagation' (>30% or rapid widening indicating structural overload).", bold_prefix="Deterioration Trend: ")

    # Section 7
    add_h1("7. Predictive Maintenance Prioritization Engine")
    add_p(
        "Municipal and state transportation authorities face constrained maintenance budgets. The maintenance engine (app/ai/maintenance.py) dynamically ranks repair actions by synthesizing asset importance tiers (High, Medium, Low), maximum damage severity score, crack growth velocity, and failure risk."
    )
    add_p(
        "Outputs include recommended repair techniques (e.g., low-viscosity epoxy pressure injection, polyurethane chemical grouting, carbon fiber polymer reinforcement, or full-depth hydrodemolition) alongside estimated budget tiers (Low, Medium, High, Capital Emergency) and mandatory completion deadlines."
    )

    # Section 8
    add_h1("8. Verification & Test Evidence")
    add_p(
        "All analytical engines were thoroughly validated through automated test suites in backend/tests/test_milestones3_4.py and verified against live image inputs:"
    )
    add_bullet("Verified geometry extraction, Zhang-Suen skeletonization, distance transform, and PCA orientation across synthetic and real crack masks.", bold_prefix="Crack Geometry Unit Tests: ")
    add_bullet("Verified boundary conditions, clamping, and tier assignment for minor, moderate, severe, and critical structural damage.", bold_prefix="Severity Engine Tests: ")
    add_bullet("Verified JET colormap blending and disk artifact generation.", bold_prefix="Grad-CAM Heatmap Tests: ")
    add_bullet("Verified multi-temporal delta calculations and accelerated deterioration trend triggers.", bold_prefix="Progression Analysis Tests: ")
    add_bullet("Verified priority level sorting, budget estimation, and repair technique assignment.", bold_prefix="Maintenance Prioritization Tests: ")

    # Section 9
    add_h1("9. Conclusion & Bridge to Milestone 4")
    add_p(
        "Milestone 3 successfully establishes InfraScan as an intelligent, quantitative civil infrastructure diagnostics suite. The system transforms qualitative photographs into actionable structural metrics, transparent Grad-CAM explainability maps, and data-driven maintenance schedules. This lays the full operational foundation for Milestone 4, which introduces automated ReportLab PDF/CSV/JSON report generation, automated notification alerts, Dockerized microservice architecture, and production frontend deployment."
    )

    doc.save(OUTPUT_PATH_1)
    doc.save(OUTPUT_PATH_2)
    doc.save(OUTPUT_PATH_3)
    print(f"Milestone 3 report saved successfully at:\n  - {OUTPUT_PATH_1}\n  - {OUTPUT_PATH_2}\n  - {OUTPUT_PATH_3}")

if __name__ == "__main__":
    build_report()
