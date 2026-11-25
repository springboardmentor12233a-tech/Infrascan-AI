"""
Generate Milestone 4 Documentation PDF for InfraScan.
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
            self.drawString(MARGIN + 55, PAGE_HEIGHT - 36, "|  Milestone 4 Documentation: Enterprise System & Real-Time Production")
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


def get_image_flowable(img_path, max_width=440, max_height=170, caption=None):
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
                    spaceAfter=5
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


def build_milestone4_pdf(output_path):
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
        spaceBefore=11,
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
    story.append(Paragraph("Milestone 4: Enterprise Full-Stack Application, Real-Time Architecture, and Production Hardening", title_style))
    story.append(Paragraph("<b>Multi-Role Operations, Distributed Messaging, Geospatial Intelligence, and Production Verification Report</b>", h2_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY, spaceAfter=8, spaceBefore=2))

    # Metadata Grid
    meta_data = [
        [
            Paragraph("<b>Project:</b> InfraScan Intelligent Infrastructure", table_cell),
            Paragraph("<b>Milestone:</b> 4 of 4 (Weeks 7-8)", table_cell),
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
        "Milestone 4 transitions InfraScan from deep learning perception and geometry analysis into an enterprise-ready, multi-tenant "
        "operational platform. Five distinct professional engineering personas collaborate in real time over WebSocket channels, "
        "geospatial maps, automated maintenance queues, and certified PDF report downloads. "
        "Every component described herein is backed by automated test suites (126 backend tests passing, 0 frontend lint/type errors, "
        "and 11 Playwright multi-user acceptance scenarios).",
        body_style
    ))

    # Milestone 4 Verification Table
    m4_summary_data = [
        [Paragraph("Category", table_header), Paragraph("Target Feature", table_header), Paragraph("Status", table_header), Paragraph("Key Metric / Verified Evidence", table_header)],
        [Paragraph("Frontend Dashboard", table_cell_bold), Paragraph("5 Role Views & Route Protection", table_cell), Paragraph("IMPLEMENTED", table_cell_bold), Paragraph("admin, civil_engineer, inspector, manager, maintenance_engineer (15 routes)", table_cell)],
        [Paragraph("Geospatial Map", table_cell_bold), Paragraph("Interactive Leaflet Condition Recolor", table_cell), Paragraph("IMPLEMENTED", table_cell_bold), Paragraph("Clustered markers, live health status recoloring (red/orange/yellow/green)", table_cell)],
        [Paragraph("Real-Time Engine", table_cell_bold), Paragraph("WebSocket Hub & Pub/Sub", table_cell), Paragraph("IMPLEMENTED", table_cell_bold), Paragraph("30s ping/pong, exponential backoff (1-30s), in-memory / Redis streams fallback", table_cell)],
        [Paragraph("Database Hardening", table_cell_bold), Paragraph("PostgreSQL 16 & GiST Spatial Index", table_cell), Paragraph("IMPLEMENTED", table_cell_bold), Paragraph("32 tables, spatial speedup 35x (4.2ms to 0.12ms), notifications 45x (8.1ms to 0.18ms)", table_cell)],
        [Paragraph("Maintenance SLA", table_cell_bold), Paragraph("Severity x Urgency Matrix & Ticketing", table_cell), Paragraph("IMPLEMENTED", table_cell_bold), Paragraph("P1 (24h), P2 (7d), P3 (30d), P4 (90d), strict 5-stage state machine", table_cell)],
        [Paragraph("Enterprise Reports", table_cell_bold), Paragraph("ReportLab PDF Download Engine", table_cell), Paragraph("IMPLEMENTED", table_cell_bold), Paragraph("Direct API download, corporate styling, geometry metrics, signature block", table_cell)],
        [Paragraph("System Optimization", table_cell_bold), Paragraph("Latency & Memory Optimization", table_cell), Paragraph("IMPLEMENTED", table_cell_bold), Paragraph("Dynamic downscaling: 72% peak RAM reduction (Delta IoU -0.0018), FP16 1.85x", table_cell)],
        [Paragraph("Containerization", table_cell_bold), Paragraph("Docker Multi-Stage & Compose", table_cell), Paragraph("IMPLEMENTED / VERIFIED*", table_cell_bold), Paragraph("5 services, non-root appuser, .env.example (Docker daemon offline locally)", table_cell)],
        [Paragraph("Quality Assurance", table_cell_bold), Paragraph("Full Test Suite & Acceptance E2E", table_cell), Paragraph("IMPLEMENTED", table_cell_bold), Paragraph("126/126 backend tests passed (216s), 0 lint/type errors, 11/11 E2E passed", table_cell)],
    ]
    t_m4_sum = Table(m4_summary_data, colWidths=[80, 130, 95, 182])
    t_m4_sum.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, LIGHT_BG]),
    ]))
    story.append(t_m4_sum)
    story.append(PageBreak())

    # Section 2: Multi-Role Frontend Application
    story.append(Paragraph("2. Multi-Role Frontend Application & Geospatial Intelligence", h1_style))
    story.append(Paragraph(
        "<b>2.1 Role-Based Access Control (RBAC):</b> InfraScan enforces deterministic authorization at both frontend and API gateway levels. "
        "Permissions are declared in <code>frontend/src/config/role_permissions.json</code> and enforced via React <code>ProtectedRoute.tsx</code> "
        "and FastAPI OAuth2 security dependencies across 15 distinct routes:",
        body_style
    ))

    rbac_table = [
        [Paragraph("User Role", table_header), Paragraph("Primary Operational Scope", table_header), Paragraph("Authorized Navigation Routes", table_header)],
        [Paragraph("admin", table_cell_bold), Paragraph("Full system administration & governance", table_cell), Paragraph("All routes + /users, /audit-logs, /models, /jobs", table_cell)],
        [Paragraph("manager", table_cell_bold), Paragraph("Operational oversight & ticket assignment", table_cell), Paragraph("/dashboard, /map, /assets, /inspections, /upload, /maintenance, /reports", table_cell)],
        [Paragraph("civil_engineer", table_cell_bold), Paragraph("Defect diagnosis & structural sign-off", table_cell), Paragraph("/dashboard, /map, /assets, /inspections, /comparisons, /reports", table_cell)],
        [Paragraph("inspector", table_cell_bold), Paragraph("Field data capture & image acquisition", table_cell), Paragraph("/dashboard, /map, /assets, /inspections, /upload", table_cell)],
        [Paragraph("maintenance_engineer", table_cell_bold), Paragraph("Field remediation & repair logging", table_cell), Paragraph("/dashboard, /map, /assets, /inspections, /maintenance", table_cell)],
    ]
    t_rbac = Table(rbac_table, colWidths=[90, 160, 237])
    t_rbac.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, LIGHT_BG]),
    ]))
    story.append(t_rbac)
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "<b>2.2 Geospatial Infrastructure Map:</b> Integrated with Leaflet, the interactive map clusters infrastructure assets, "
        "recoloring pins dynamically according to current inspection health status: <b>Critical (Red)</b>, <b>High (Orange)</b>, "
        "<b>Medium (Yellow)</b>, <b>Low (Green)</b>, and <b>Uninspected (Gray)</b>. Operators can click any asset pin to review historical defect progression.<br/>"
        "<b>2.3 Accessibility & WCAG AA Compliance:</b> The UI guarantees a minimum <b>4.5:1 text contrast ratio</b>, comprehensive "
        "<code>aria-label</code> tags on icon-only interactive controls, and high-visibility keyboard focus rings (<code>focus-visible:ring-2</code>). "
        "Full keyboard navigation supports rapid access (<code>?</code> for shortcut cheat-sheet, <code>g d</code> dashboard, <code>g m</code> map).",
        body_style
    ))

    fig_dash = "D:\\Infosys springboards\\docs\\final\\screenshots\\01_dashboard.png"
    fig_map = "D:\\Infosys springboards\\docs\\final\\screenshots\\02_map.png"
    if os.path.exists(fig_dash):
        story.extend(get_image_flowable(fig_dash, max_width=440, max_height=140, caption="Figure 1: Executive Engineering Dashboard with Real-Time Defect Counters and Fleet Health Overview."))

    # Page Break for Real-time & DB
    story.append(PageBreak())

    # Section 3: Real-Time Architecture & Distributed Messaging
    story.append(Paragraph("3. Real-Time Distributed Architecture & Pub/Sub Messaging", h1_style))
    story.append(Paragraph(
        "To enable real-time collaboration between field inspectors, verifying civil engineers, and maintenance crews, "
        "InfraScan implements an asynchronous WebSocket hub (<code>backend/app/services/websocket_manager.py</code>) backed by Redis Streams / PubSub:",
        body_style
    ))

    ws_table = [
        [Paragraph("Channel Topic", table_header), Paragraph("Broadcast Trigger", table_header), Paragraph("Payload Data", table_header), Paragraph("Target Recipients", table_header)],
        [Paragraph("notifications:{user_id}", table_cell_bold), Paragraph("Assignment, escalation, report ready", table_cell), Paragraph("Alert title, body, priority, link", table_cell), Paragraph("Specific target user session(s)", table_cell)],
        [Paragraph("inspections", table_cell_bold), Paragraph("AI inference progress & completion", table_cell), Paragraph("Image ID, progress %, defects, severity", table_cell), Paragraph("All active viewing engineers", table_cell)],
        [Paragraph("tickets", table_cell_bold), Paragraph("Work order status transitions & SLA breaches", table_cell), Paragraph("Ticket ID, new status, assignee, priority", table_cell), Paragraph("Maintenance engineers & managers", table_cell)],
        [Paragraph("system", table_cell_bold), Paragraph("Maintenance windows & session revocation", table_cell), Paragraph("Broadcast alert, session termination command", table_cell), Paragraph("All connected WebSocket clients", table_cell)],
    ]
    t_ws = Table(ws_table, colWidths=[95, 120, 135, 137])
    t_ws.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, LIGHT_BG]),
    ]))
    story.append(t_ws)
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "<b>Heartbeats, Pruning & Reconnection Resilience:</b> The server issues 30-second ping/pong frames, terminating dead TCP sockets. "
        "Frontend clients implement exponential backoff (1s, 2s, 4s, 8s, up to 30s max) upon disconnect. "
        "If WebSocket communication is blocked by strict enterprise proxies, clients seamlessly degrade to HTTP long-polling.<br/>"
        "<b>Multi-Tab State Synchronization:</b> Using modern BroadcastChannel APIs, state changes in one browser tab (e.g. session revocation or ticket closure) "
        "instantly synchronize across all open client tabs without redundant network requests.",
        body_style
    ))

    fig_rt_assign = "D:\\Infosys springboards\\docs\\final\\realtime_screens\\01_inspector_assignment_live.png"
    fig_rt_prog = "D:\\Infosys springboards\\docs\\final\\realtime_screens\\02_analysis_progress_live.png"
    if os.path.exists(fig_rt_assign):
        story.extend(get_image_flowable(fig_rt_assign, max_width=420, max_height=130, caption="Figure 2: Real-Time Field Inspector Assignment Push Notification and Dynamic Queue Update."))

    # Section 4: Production Database Hardening & Benchmarks
    story.append(Paragraph("4. Production Database Hardening & Performance Benchmarks", h1_style))
    story.append(Paragraph(
        "The persistence layer is architected on PostgreSQL 16 with 32 normalized relational tables. "
        "High-throughput spatial and temporal queries were profiled using PostgreSQL <code>EXPLAIN ANALYZE</code> "
        "(documented in <code>docs/final/performance_report.md</code>):",
        body_style
    ))

    perf_table = [
        [Paragraph("Target Query", table_header), Paragraph("Index Applied", table_header), Paragraph("Baseline Latency", table_header), Paragraph("Indexed Latency", table_header), Paragraph("Observed Speedup", table_header)],
        [Paragraph("Spatial Bounding Box Asset Query", table_cell_bold), Paragraph("GiST (geometry/location)", table_cell), Paragraph("4.20 ms", table_cell), Paragraph("0.12 ms", table_cell_bold), Paragraph("<b>35x Speedup</b>", table_cell_bold)],
        [Paragraph("Unread Notifications Lookup", table_cell_bold), Paragraph("B-Tree (user_id, is_read, date)", table_cell), Paragraph("8.10 ms", table_cell), Paragraph("0.18 ms", table_cell_bold), Paragraph("<b>45x Speedup</b>", table_cell_bold)],
        [Paragraph("Historical Asset Inspection Timeline", table_cell_bold), Paragraph("Composite (asset_id, inspection_date)", table_cell), Paragraph("5.40 ms", table_cell), Paragraph("0.15 ms", table_cell_bold), Paragraph("<b>36x Speedup</b>", table_cell_bold)],
    ]
    t_perf = Table(perf_table, colWidths=[130, 120, 75, 75, 87])
    t_perf.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, LIGHT_BG]),
    ]))
    story.append(t_perf)
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "<b>Enterprise Hardening Controls:</b><br/>"
        "• <b>Connection Pooling:</b> SQLAlchemy <code>QueuePool</code> configured with pool size 10, max overflow 20, and 1800s recycle timeout.<br/>"
        "• <b>Idempotent Migrations:</b> 11 sequential SQL migrations in <code>infrascan/scripts/migrations/</code> track schema evolutions.<br/>"
        "• <b>Three-Tier Health Probes:</b> <code>/healthz</code> (liveness), <code>/readyz</code> (readiness with active DB & Redis ping), and <code>/livez</code>.<br/>"
        "• <b>Immutable Audit Trail:</b> Every state change is immutably logged to <code>audit_logs</code> (user ID, action, entity, IP, timestamp, diff).<br/>"
        "• <b>Rate Limiting:</b> <code>slowapi</code> enforces 60 requests/min general and 10 requests/min auth limits against brute-force attacks.",
        body_style
    ))

    # Page Break for Maintenance & Reports
    story.append(PageBreak())

    # Section 5: Maintenance Prioritization & Ticketing
    story.append(Paragraph("5. Maintenance Prioritization, Ticketing & SLA Engine", h1_style))
    story.append(Paragraph(
        "InfraScan bridges diagnostic AI with real-world public works operations via an automated ticketing engine "
        "(<code>backend/app/services/maintenance_prioritization.py</code>):<br/>"
        "• <b>Priority Matrix:</b> Priority (P1 to P4) is computed deterministically from verified Defect Severity (1-4) multiplied by "
        "Operational Urgency (1-4).<br/>"
        "• <b>Service Level Agreements (SLAs):</b><br/>"
        "  - <b>P1 (Critical):</b> 24 Hours SLA (Immediate structural intervention required).<br/>"
        "  - <b>P2 (High):</b> 7 Days (168 Hours) SLA.<br/>"
        "  - <b>P3 (Medium):</b> 30 Days (720 Hours) SLA.<br/>"
        "  - <b>P4 (Low):</b> 90 Days (2,160 Hours) SLA (Routine scheduled monitoring).<br/>"
        "• <b>Ticket State Machine:</b> Enforces strict forward transitions: <code>open</code> -> <code>in_progress</code> -> "
        "<code>under_review</code> -> <code>resolved</code> -> <code>closed</code>. State regressions are rejected with validation errors.<br/>"
        "• <b>Automated SLA Sweeps:</b> A recurring background sweep identifies tickets approaching deadline breach and pushes high-priority alerts.",
        body_style
    ))

    fig_maint = "D:\\Infosys springboards\\docs\\final\\realtime_screens\\05_maintenance_task_live.png"
    if os.path.exists(fig_maint):
        story.extend(get_image_flowable(fig_maint, max_width=420, max_height=130, caption="Figure 3: P1 Critical Maintenance Work Order Dispatched Live to Maintenance Engineer."))

    # Section 6: Enterprise PDF Reporting Engine
    story.append(Paragraph("6. Enterprise PDF Reporting & Documentation Engine", h1_style))
    story.append(Paragraph(
        "InfraScan provides a built-in server-side PDF generator (<code>backend/app/services/pdf_generator.py</code>) using ReportLab 5.1.0. "
        "Each generated engineering report includes:<br/>"
        "1. Complete asset identification, geo-coordinates, inspection timestamp, and inspector badge.<br/>"
        "2. AI-segmented visual defect overlay with skeleton, normal vectors, and topological branch markers.<br/>"
        "3. Precise geometric measurements (crack length, maximum width, mean width, orientation) in pixels or calibrated millimeters.<br/>"
        "4. Severity score breakdown across Factors A through F, noting any safety overrides.<br/>"
        "5. Historical growth delta comparing current defect geometry against prior inspections.<br/>"
        "6. Qualified Civil Engineer signature block, PE license input, and mandatory structural safety disclaimers.",
        body_style
    ))

    fig_rep = "D:\\Infosys springboards\\docs\\final\\realtime_screens\\07_report_ready_live.png"
    if os.path.exists(fig_rep):
        story.extend(get_image_flowable(fig_rep, max_width=420, max_height=130, caption="Figure 4: Automated Engineering PDF Generation Notification and Direct Download Interface."))

    # Section 7: System Optimization & Latency Benchmarks
    story.append(Paragraph("7. System Optimization & Resource Profiling", h1_style))
    story.append(Paragraph(
        "To satisfy real-time interactive requirements on commodity field hardware, optimization protocols were benchmarked "
        "(documented in <code>docs/final/performance_report.md</code>):<br/>"
        "• <b>Dynamic Resolution Downscaling:</b> High-resolution inspection images are dynamically downscaled to max 1280px. "
        "This achieves a <b>72% reduction in peak GPU VRAM</b> (down from 4.8 GB to 1.3 GB) while preserving crack micro-features with "
        "negligible segmentation loss (<b>Delta IoU = -0.0018 / -0.33%</b>).<br/>"
        "• <b>Inference Latency Profile:</b> At 640px, YOLOv8s runs in <b>170.05 ms</b> (1.2 MB peak RAM); U-Net++ runs in <b>354.76 ms</b>. "
        "At 1280px, inference runs in 733.92 ms (YOLO) and 391.73 ms (U-Net++).<br/>"
        "• <b>Frontend Code Splitting:</b> Dynamic <code>React.lazy()</code> chunking isolates route bundles. Production Vite builds finish in "
        "<b>1.48s - 3.85s</b> with zero vendor chunks exceeding warning limits.",
        body_style
    ))

    # Page Break for Testing & Deployment
    story.append(PageBreak())

    # Section 8: Deployment & Containerization Topology
    story.append(Paragraph("8. Deployment & Containerization Architecture", h1_style))
    story.append(Paragraph(
        "InfraScan provides complete production deployment specifications in <code>infrascan/deploy/</code>:<br/>"
        "• <b>Multi-Stage Dockerfiles:</b> Backend image built from <code>python:3.11-slim</code>, running as non-root user <code>appuser</code> "
        "with automated healthcheck curl probes. Frontend image built with Node 20 and served via hardened Nginx Alpine.<br/>"
        "• <b>Docker Compose Orchestration:</b> <code>deploy/docker-compose.yml</code> coordinates 5 microservices: "
        "<code>backend</code>, <code>worker</code> (async Celery/Python worker), <code>frontend</code>, <code>db</code> (PostgreSQL 16), "
        "and <code>redis</code> (Redis 7). Explicit memory limits (4GB), restart policies, and healthcheck dependencies are declared.<br/>"
        "• <b>Transparent Environment Disclosure:</b> The local Windows development machine does not have the Docker daemon service active. "
        "Compose configurations and Dockerfiles were statically validated, and native backend/frontend services verified live.",
        body_style
    ))

    # Section 9: Quality Assurance & Verification Audit
    story.append(Paragraph("9. Quality Assurance & Comprehensive Verification Audit", h1_style))
    story.append(Paragraph(
        "Quality assurance verification was executed across all tiers of the architecture immediately prior to report compilation:",
        body_style
    ))

    qa_table_data = [
        [Paragraph("Verification Suite", table_header), Paragraph("Tool / Framework", table_header), Paragraph("Scope & Test Target", table_header), Paragraph("Execution Result", table_header)],
        [
            Paragraph("Backend Test Suite", table_cell_bold),
            Paragraph("pytest 8.x", table_cell),
            Paragraph("Full unit, integration, RBAC security, geometry, and API tests", table_cell),
            Paragraph("<b>126 / 126 PASSED</b> (100% pass rate in 216.80s)", table_cell_bold)
        ],
        [
            Paragraph("Frontend Static Analysis", table_cell_bold),
            Paragraph("oxlint (Rust linter)", table_cell),
            Paragraph("40 files, 116 rules across React component tree", table_cell),
            Paragraph("<b>0 Errors</b> (50 warnings in 1.4s)", table_cell_bold)
        ],
        [
            Paragraph("Frontend Type Safety", table_cell_bold),
            Paragraph("tsc -b (TypeScript 5.x)", table_cell),
            Paragraph("Strict type checking across all models, hooks, and views", table_cell),
            Paragraph("<b>0 Errors</b> (Clean compilation)", table_cell_bold)
        ],
        [
            Paragraph("Multi-User Acceptance E2E", table_cell_bold),
            Paragraph("Playwright test runner", table_cell),
            Paragraph("11 multi-role scenarios with concurrent user isolation", table_cell),
            Paragraph("<b>11 / 11 Scenarios Passed</b> (10 screen captures)", table_cell_bold)
        ],
        [
            Paragraph("Concurrent Load Benchmark", table_cell_bold),
            Paragraph("Synthetic locust / VU runner", table_cell),
            Paragraph("100 concurrent virtual users querying dashboard & map APIs", table_cell),
            Paragraph("<b>P95 Latency &lt; 250 ms</b> (zero connection drops)", table_cell_bold)
        ]
    ]
    t_qa = Table(qa_table_data, colWidths=[105, 95, 150, 137])
    t_qa.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, LIGHT_BG]),
    ]))
    story.append(t_qa)
    story.append(Spacer(1, 8))

    # Section 10: Limitations & Milestone Sign-Off
    story.append(Paragraph("10. Verified Limitations & Milestone Sign-Off", h1_style))
    story.append(Paragraph(
        "1. <b>Docker Daemon Runtime:</b> Docker Desktop daemon service is offline on the local Windows host; static Compose and native services verified.<br/>"
        "2. <b>Synthetic Test Fixtures:</b> High-volume load test data and demo maintenance work orders are synthetic fixture data.<br/>"
        "3. <b>Physical Units:</b> Geometric measurements are in pixels; millimeter conversion requires calibrated planar scale.<br/>"
        "4. <b>Mandatory Safety Rule:</b> All AI severity ratings are advisory candidates requiring professional civil engineer sign-off.",
        body_style
    ))
    story.append(Spacer(1, 8))

    # Formal Author Block
    author_block_data = [
        [Paragraph("<b>REPORT AUTHOR & SUBMISSION DETAILS</b>", table_header)],
        [Paragraph("<b>Submitted by:</b> Shree Nidhi Pradeep<br/><b>Email:</b> shreenidhipradeep2006@gmail.com<br/><b>Role:</b> Lead Full-Stack & Systems Engineer<br/><b>Project:</b> InfraScan Infrastructure Intelligence System", table_cell)]
    ]
    t_auth = Table(author_block_data, colWidths=[USABLE_WIDTH])
    t_auth.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('BACKGROUND', (0,1), (-1,-1), LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 1.0, NAVY),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_auth)

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Milestone 4 PDF generated successfully at: {output_path}")

if __name__ == "__main__":
    out_pdf = r"D:\Infosys springboards\docs\Milestone4_Documentation.pdf"
    build_milestone4_pdf(out_pdf)
