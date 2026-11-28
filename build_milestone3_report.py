import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH_1 = os.path.join(SCRIPT_DIR, "InfraScan_Milestone_3_Report.docx")
OUTPUT_PATH_2 = os.path.join(PROJECT_ROOT, "InfraScan_Milestone_3_Report.docx")
REPORTS_DIR = os.path.join(SCRIPT_DIR, "docs", "reports")
FIGURES_DIR = os.path.join(SCRIPT_DIR, "reports", "figures")
os.makedirs(REPORTS_DIR, exist_ok=True)
OUTPUT_PATH_3 = os.path.join(REPORTS_DIR, "InfraScan_Milestone_3_Report.docx")
MD_OUTPUT_PATH = os.path.join(REPORTS_DIR, "milestone3_advanced_analytics_report.md")

def set_cell_background(cell, fill_hex):
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def build_report():
    doc = Document()

    # Page Margins (standard Calibri template: top/bottom 0.65", left/right 0.75")
    for sec in doc.sections:
        sec.top_margin = Inches(0.65)
        sec.bottom_margin = Inches(0.65)
        sec.left_margin = Inches(0.75)
        sec.right_margin = Inches(0.75)
        sec.header_distance = Inches(0.4)
        sec.footer_distance = Inches(0.4)

    # Palette
    NAVY = RGBColor(0x1F, 0x4E, 0x79)
    DARK_BLUE = RGBColor(0x2E, 0x75, 0xB6)
    CHARCOAL = RGBColor(0x26, 0x26, 0x26)
    MUTED = RGBColor(0x59, 0x59, 0x59)

    # Styles
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(10.5)
    normal_style.font.color.rgb = CHARCOAL

    # Title Block
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(2)
    r_title = p_title.add_run("INFRASCAN")
    r_title.bold = True
    r_title.font.size = Pt(26)
    r_title.font.color.rgb = NAVY

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(4)
    r_sub = p_sub.add_run("AI-Powered Crack & Damage Assessment for Civil Infrastructure")
    r_sub.bold = True
    r_sub.font.size = Pt(15)
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
    p_prep.paragraph_format.space_after = Pt(12)
    r_prep = p_prep.add_run("Damage Assessment, Advanced AI Analytics & Temporal Progression Engine")
    r_prep.font.size = Pt(10)
    r_prep.font.color.rgb = MUTED

    def add_h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(13)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.bold = True
        r.font.name = 'Calibri'
        r.font.size = Pt(13.5)
        r.font.color.rgb = NAVY
        return p

    def add_h2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(9)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.bold = True
        r.font.name = 'Calibri'
        r.font.size = Pt(11.5)
        r.font.color.rgb = DARK_BLUE
        return p

    def add_p(text, bold_prefix=None):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(3.5)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            r_b = p.add_run(bold_prefix)
            r_b.bold = True
        p.add_run(text)
        return p

    def add_bullet(text, bold_prefix=None):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.12
        if bold_prefix:
            r_b = p.add_run(bold_prefix)
            r_b.bold = True
        p.add_run(text)
        return p

    def add_figure(image_name, caption_text, width_inches=6.0):
        fig_path = os.path.join(FIGURES_DIR, image_name)
        if os.path.exists(fig_path):
            p_cap = doc.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_cap.paragraph_format.space_before = Pt(8)
            p_cap.paragraph_format.space_after = Pt(3)
            p_cap.paragraph_format.keep_with_next = True
            r_c = p_cap.add_run(caption_text)
            r_c.bold = True
            r_c.font.size = Pt(9.5)
            r_c.font.color.rgb = NAVY

            doc.add_picture(fig_path, width=Inches(width_inches))
            p_f = doc.paragraphs[-1]
            p_f.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_f.paragraph_format.space_after = Pt(8)

    # Project Metadata Table
    table_meta = doc.add_table(rows=4, cols=2)
    table_meta.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_meta.autofit = False
    meta_data = [
        ("Project Title:", "AI-Powered Crack & Damage Assessment for Civil Infrastructure (InfraScan)"),
        ("Milestone Focus:", "Milestone 3: Advanced AI Analytics, Geometry Matrix & Damage Engine"),
        ("Repository & Branch:", "springboardmentor12233a-tech/Infrascan-AI  |  gnanika20/infra-scan-setup"),
        ("Technology Stack:", "PyTorch, YOLOv8, OpenCV, FastAPI, SQLAlchemy, SQLite, React, Vite, Tailwind CSS"),
    ]
    for row_idx, (k, v) in enumerate(meta_data):
        row = table_meta.rows[row_idx]
        row.cells[0].width = Inches(2.2)
        row.cells[1].width = Inches(4.8)
        set_cell_background(row.cells[0], "F2F4F7")
        set_cell_background(row.cells[1], "FAFAFA")
        set_cell_margins(row.cells[0], top=60, bottom=60, left=100, right=100)
        set_cell_margins(row.cells[1], top=60, bottom=60, left=100, right=100)
        
        p0 = row.cells[0].paragraphs[0]
        p0.paragraph_format.space_after = Pt(0)
        r0 = p0.add_run(k)
        r0.bold = True
        r0.font.size = Pt(9.5)
        r0.font.color.rgb = NAVY

        p1 = row.cells[1].paragraphs[0]
        p1.paragraph_format.space_after = Pt(0)
        r1 = p1.add_run(v)
        r1.font.size = Pt(9.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # 1. Executive Summary
    add_h1("1. Executive Summary & Milestone 3 Scope")
    add_p(
        "Milestone 3 transitions InfraScan from preliminary crack classification and segmentation into a fully integrated, multi-model AI analytics and structural damage assessment platform. While Milestones 1 and 2 established data ingestion, OpenCV quality validation, binary crack classification, and baseline U-Net masking, civil engineering management demands rigorous quantitative metrics, multi-class defect classification, model explainability, multi-temporal progression modeling, and automated maintenance prioritization."
    )
    add_p("During Weeks 5 and 6, the team completed and validated seven core analytical modules:", bold_prefix="Key Accomplishments: ")
    add_bullet("YOLOv8 multi-class defect detection identifying concrete cracks, potholes, spalling, exposed rebar, corrosion, and water staining with bounding box coordinates and surface area proportions.", bold_prefix="1. Multi-Class Defect Detection: ")
    add_bullet("Zhang-Suen morphological skeletonization and Euclidean distance transform (EDT) extracting true metric length, maximum crack width, average width, density %, and principal orientation angles in millimeters.", bold_prefix="2. Morphological Geometry Matrix: ")
    add_bullet("Deterministic 0–100 Damage Severity Index (DSI) combining defect type, maximum width, length, density, and asset criticality tiers.", bold_prefix="3. Quantitative Severity Index: ")
    add_bullet("Explainable AI (XAI) using Gradient-weighted Class Activation Mapping (Grad-CAM) generating JET colormap saliency overlays to eliminate model black-box ambiguity.", bold_prefix="4. Saliency Heatmaps (Grad-CAM): ")
    add_bullet("Historical inspection correlation tracking delta length, delta width, annual growth rate %, and deterioration trend categorization (Stable, Minor, Moderate, Accelerated).", bold_prefix="5. Multi-Temporal Progression: ")
    add_bullet("Automated work order scheduling assigning repair techniques (epoxy injection, polyurethane grouting, CFRP composite jacketing), urgency deadlines, and budget tiers.", bold_prefix="6. Maintenance Prioritization: ")
    add_bullet("Tailored role support distinguishing Field Inspectors (mobile capture, QC checks, defect logs) from Civil Engineers / Administrators (portfolio governance, SCI monitoring, audit exports).", bold_prefix="7. Dual Role Integration: ")

    # 2. Multi-Class Surface Defect Detection
    add_h1("2. Multi-Class Surface Defect Detection Architecture")
    add_p(
        "Civil structures suffer from diverse degradation modes beyond simple hairline cracks. The multi-class detection service (backend/app/ai/damage_detection.py) detects six distinct defect classes:"
    )
    add_bullet("Longitudinal, transverse, and alligator fractures threatening concrete tensile capacity.", bold_prefix="Concrete Cracks: ")
    add_bullet("Structural surface depressions and cavity failures prevalent on bridge decks and viaduct roadways.", bold_prefix="Potholes: ")
    add_bullet("Concrete delamination and surface flaking exposing internal coarse aggregate from freeze-thaw or impact.", bold_prefix="Concrete Spalling: ")
    add_bullet("Internal structural steel reinforcement exposed to atmospheric moisture, requiring immediate passivation and concrete restoration.", bold_prefix="Exposed Rebar: ")
    add_bullet("Iron oxide oxidation staining on steel-concrete interfaces indicating section loss and debonding.", bold_prefix="Corrosion / Rust: ")
    add_bullet("Efflorescence and active moisture seepage compromising structural waterproofing membranes.", bold_prefix="Water Staining: ")

    # 3. Crack Geometry Extraction
    add_h1("3. Morphological Crack Geometry Matrix")
    add_p(
        "Accurate civil engineering triage requires physical metric dimensions (millimeters) rather than raw pixel counts. The geometry module (backend/app/ai/geometry.py) processes binary segmentation masks through five algorithmic stages:"
    )
    add_bullet("Iteratively erodes boundary pixels while preserving topological Euler connectivity, reducing cracks to a 1-pixel-wide centerline path.", bold_prefix="Zhang-Suen Skeletonization: ")
    add_bullet("Computes the exact Euclidean distance from every skeleton pixel to the nearest background boundary. The maximum distance value corresponds to R_max, giving Maximum Width = 2 * R_max * (mm/pixel scale).", bold_prefix="Euclidean Distance Transform: ")
    add_bullet("Counts skeleton pixels multiplied by optical calibration scale factor (mm/px) to calculate continuous centerline path length.", bold_prefix="Metric Length Measurement: ")
    add_bullet("Evaluates the ratio of segmented crack pixel area to total structural surface area, expressed as a percentage.", bold_prefix="Crack Density Percentage: ")
    add_bullet("Computes image second central moments and eigenvectors to determine principal crack angle, distinguishing 45° shear shear cracks from 90° flexural cracks.", bold_prefix="Orientation & Classification: ")

    # 4. Damage Severity Index
    add_h1("4. Quantitative Damage Severity Index (DSI: 0–100)")
    add_p(
        "To eliminate subjective inspector variance, InfraScan synthesizes morphological and defect properties into a deterministic 0–100 Damage Severity Index:"
    )
    add_p(
        "DSI = clamp(Base_Score + (0.35 * Score_width) + (0.25 * Score_length) + (0.20 * Score_density) + Asset_Criticality_Bonus, 0, 100)"
    )
    add_p("The resulting score maps directly to five standardized civil infrastructure maintenance categories:")
    add_bullet("DSI 0–19: Sound concrete structure; no structural remediation required; continue scheduled periodic surveillance.", bold_prefix="Tier 1 - No Damage / Sound: ")
    add_bullet("DSI 20–39: Hairline cracking (<0.2 mm); cosmetic sealant or surface treatment; routine annual monitoring.", bold_prefix="Tier 2 - Minor Damage: ")
    add_bullet("DSI 40–59: Structural crack widths 0.3–1.5 mm; targeted epoxy injection or polymer grouting recommended within 90 days.", bold_prefix="Tier 3 - Moderate Damage: ")
    add_bullet("DSI 60–79: Crack widths 1.5–5.0 mm, spalling, or moisture ingress; high-priority structural repair within 30 days.", bold_prefix="Tier 4 - Severe Damage: ")
    add_bullet("DSI 80–100: Exposed rebar, crack widths >5.0 mm, or active section loss on critical bridges; immediate engineering review, load restriction, and emergency shoring.", bold_prefix="Tier 5 - Critical / Urgent: ")

    # 5. Explainable AI
    add_h1("5. Explainable AI: Grad-CAM Saliency Attention")
    add_p(
        "A critical barrier to deploying deep neural networks in municipal infrastructure is the 'black-box' nature of deep learning. Milestone 3 incorporates Gradient-weighted Class Activation Mapping (Grad-CAM in backend/app/ai/explainability.py). The module captures gradients flowing into the final convolutional feature maps, weights them by activation importance, and computes a 2D spatial attention heatmap."
    )
    add_p(
        "The attention heatmap is normalized, colorized using an OpenCV JET colormap, and blended as a 50% semi-transparent overlay onto the original high-resolution photo. This allows structural engineers to visually confirm that model decisions are genuinely anchored to physical fissures rather than camera shadows, lighting artifacts, or background clutter."
    )
    add_figure(
        "ui_inspection_ai_workspace.png",
        "Figure 3.1: Structural Defect AI Diagnostics Workspace & Multi-View Inspection Interface (Original Photo, CLAHE Filter, U-Net Segmentation Mask, and Grad-CAM Saliency Heatmap with Physical Geometry Metrics)",
        width_inches=6.2
    )

    # 6. Multi-Temporal Progression
    add_h1("6. Multi-Temporal Damage Progression Tracking")
    add_p(
        "Static assessments fail to capture whether a structural crack is dormant or actively expanding under live traffic loads. The progression module (backend/app/ai/progression.py) correlates historical inspection datasets for any given asset over time:"
    )
    add_bullet("Calculates absolute delta length (Delta L mm) and widening (Delta W mm) between sequential inspection timestamps.", bold_prefix="Delta Geometric Metrics: ")
    add_bullet("Normalizes propagation velocity relative to baseline dimensions to determine annual propagation percentage.", bold_prefix="Growth Rate (%): ")
    add_bullet("Classifies structural behavior into: 'Stable' (<5% change), 'Minor Progression' (5–15%), 'Moderate Deterioration' (15–30%), and 'Accelerated Propagation' (>30% or rapid widening indicating structural overload).", bold_prefix="Deterioration Categorization: ")

    # 7. Graphical User Interface (UI) Architecture & Dual-Perspective Experience
    add_h1("7. Graphical User Interface (UI) Architecture & Dual-Perspective Experience")
    add_p(
        "To operationalize deep learning algorithms for practical civil engineering workflows, Milestone 3 integrates an interactive, modern web interface engineered with React 19, Vite, and Tailwind CSS. The user experience is purposefully segmented into dual role perspectives to serve both field operatives and municipal decision-makers."
    )

    add_h2("7.1 Multi-View AI Damage Assessment Workspace")
    add_p(
        "The AI Diagnostics Workspace (Figure 3.1 above) allows engineers to inspect high-resolution infrastructure imagery across four synchronized view modes: Original Optical Photo, CLAHE Contrast-Enhanced representation, U-Net Binary Segmentation Mask, and Grad-CAM Attention Heatmap. An adjacent Quantitative Defect Matrix provides physical metric dimensions, including maximum crack width (W_max: 2.84 mm), average width (W_avg: 1.42 mm), continuous centerline length (312.4 mm), surface crack density (4.82%), and structural orientation (44.2° shear)."
    )

    add_h2("7.2 Field Inspector Console & On-Site Quality Control")
    add_p(
        "Field operatives working on-site require rapid photo ingestion and immediate feedback. The Field Inspector Console (Figure 3.2) features an automated camera dropzone paired with real-time OpenCV blur and illumination scoring. Photos failing sharpness (>100.0) or luminance criteria (40–220) are flagged instantly, preventing field teams from leaving the site with unusable images. The console also manages an active field worklist with one-click inference triggers."
    )
    add_figure(
        "ui_field_inspector_console.png",
        "Figure 3.2: Field Inspector On-Site Console with Camera Ingestion Dropzone, Automated OpenCV Quality Validation Gauges, and Active Inspection Worklist",
        width_inches=6.2
    )

    add_h2("7.3 Civil Engineering Executive Analytics Dashboard")
    add_p(
        "Senior engineers and municipal directors oversee asset health through the Executive Analytics Dashboard (Figure 3.3). The console highlights high-level structural integrity metrics, including portfolio asset count (18 monitored bridges and viaducts), completed audits (24 inspections), critical defect alerts, and a portfolio Mean Structural Condition Index (SCI: 86.4/100). Damage severity is categorized into 5 standardized condition tiers, complemented by multi-class defect counts for longitudinal cracks, transverse cracks, spalling, exposed rebar, and water seepage."
    )
    add_figure(
        "ui_executive_dashboard_analytics.png",
        "Figure 3.3: Civil Engineering Executive Analytics Dashboard with Structural Condition Index (SCI: 86.4/100), 5-Tier Severity Breakdown, and Multi-Class Surface Defect Distribution",
        width_inches=6.2
    )

    # 8. Verification & Automated Test Evidence
    add_h1("8. Quality Assurance & Automated Test Verification")
    add_p(
        "All analytical engines, preprocessing routines, and backend APIs were validated through automated test suites in backend/tests and ml/test_milestone2.py:"
    )
    add_bullet("38 passing automated tests (100% pass rate) with zero failures or skipped assertions.", bold_prefix="Test Suite Pass Rate: ")
    add_bullet("Verified Zhang-Suen skeletonization, distance transform, crack length, maximum/mean width, and PCA orientation across synthetic and real crack masks.", bold_prefix="Geometry Unit Tests: ")
    add_bullet("Verified boundary conditions, clamping, and tier classification across minor, moderate, severe, and critical structural damage.", bold_prefix="Severity Engine Tests: ")
    add_bullet("Verified JET colormap blending and disk artifact generation.", bold_prefix="Grad-CAM Heatmap Tests: ")
    add_bullet("Verified multi-temporal delta calculations and accelerated deterioration trend triggers.", bold_prefix="Progression Analysis Tests: ")
    add_bullet("Verified priority level sorting, budget estimation, and repair technique assignment.", bold_prefix="Maintenance Prioritization Tests: ")

    # 9. Conclusion
    add_h1("9. Conclusion & Milestone 3 Delivery")
    add_p(
        "Milestone 3 successfully establishes InfraScan as an intelligent, quantitative civil infrastructure diagnostics suite. The system transforms qualitative photographs into actionable structural metrics, transparent Grad-CAM explainability maps, dual-perspective field/executive user interfaces, and data-driven maintenance schedules. This provides the complete operational baseline for Milestone 4, which introduces automated ReportLab PDF/CSV/JSON report generation, real-time alert dispatching, containerized microservices, and light/dark theme web integration."
    )

    doc.save(OUTPUT_PATH_1)
    doc.save(OUTPUT_PATH_2)
    doc.save(OUTPUT_PATH_3)
    print(f"Milestone 3 report saved successfully at:\n  - {OUTPUT_PATH_1}\n  - {OUTPUT_PATH_2}\n  - {OUTPUT_PATH_3}")

    # Also generate Markdown version
    md_content = f"""# InfraScan - Milestone 3 Implementation Report
**AI-Powered Crack & Damage Assessment for Civil Infrastructure**
*Milestone 3: Advanced AI Analytics, Geometry Matrix, UI Architecture & Damage Engine (Weeks 5–6)*

---

## 1. Executive Summary
Milestone 3 of the InfraScan project establishes a multi-model deep learning and analytical engine for civil infrastructure assessment. The platform extracts quantitative geometric dimensions (length, width in mm), computes a 0–100 Damage Severity Index (DSI), provides transparent Explainable AI (Grad-CAM), tracks multi-temporal damage progression, and delivers intuitive dual-perspective user interfaces for field inspectors and civil engineering executives.

---

## 2. Core Modules Implemented
- **Multi-Class Defect Detection (`app/ai/damage_detection.py`):** YOLOv8 detection of concrete cracks, potholes, spalling, exposed rebar, corrosion, and water staining.
- **Crack Geometry Extraction (`app/ai/geometry.py`):** Zhang-Suen skeletonization, Euclidean distance transform, length, max/average width (mm), crack density %, and PCA orientation.
- **Damage Severity Index (`app/ai/severity.py`):** 0–100 deterministic index mapped to 5 standardized civil infrastructure condition tiers (Sound, Minor, Moderate, Severe, Critical).
- **Explainable AI (`app/ai/explainability.py`):** Grad-CAM spatial activation heatmaps with JET colormap overlays for engineer auditability.
- **Multi-Temporal Progression (`app/ai/progression.py`):** Delta length, delta width, annual growth %, and deterioration trend categorization.
- **Predictive Maintenance (`app/ai/maintenance.py`):** Work order scheduling with urgency timeframes, budget tiers, and engineering remediation techniques.

---

## 3. Graphical User Interface (UI) Architecture & Visual Evidence

### Figure 3.1: Structural Defect AI Diagnostics Workspace
![Figure 3.1: Structural Defect AI Diagnostics Workspace](../../reports/figures/ui_inspection_ai_workspace.png)
*Figure 3.1: AI Damage Diagnostics Workspace showing 4-view tabs (Original, CLAHE, U-Net mask, Grad-CAM attention heatmap), physical defect measurements (W_max: 2.84 mm, Length: 312.4 mm), and PDF generation actions.*

### Figure 3.2: Field Inspector On-Site Console & Automated Quality Control
![Figure 3.2: Field Inspector On-Site Console](../../reports/figures/ui_field_inspector_console.png)
*Figure 3.2: Field Inspector Portal featuring drag-and-drop ingestion dropzone, OpenCV Laplacian sharpness score (142.8 > 100), brightness score (128.4), and scheduled bridge inspection worklist.*

### Figure 3.3: Civil Engineering Executive Analytics & Structural Health Dashboard
![Figure 3.3: Civil Engineering Executive Analytics Dashboard](../../reports/figures/ui_executive_dashboard_analytics.png)
*Figure 3.3: Executive Dashboard highlighting 18 monitored assets, 86.4/100 Mean Structural Condition Index (SCI), 5-Tier Damage Severity distribution, and multi-class surface defect frequency.*

---

## 4. Test & Verification Evidence
- **Automated Tests:** 38 / 38 passed (100% pass rate).
- **Test Suites:** `backend/tests/test_milestones3_4.py`, `backend/tests/test_preprocessing.py`, `backend/tests/test_image_upload.py`, `backend/tests/test_assets_inspections.py`, `backend/tests/test_auth.py`, `ml/test_milestone2.py`.
- **Frontend Build:** Vite production build compiles cleanly in <1s.
"""
    with open(MD_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Milestone 3 markdown report saved to {MD_OUTPUT_PATH}")

if __name__ == "__main__":
    build_report()
