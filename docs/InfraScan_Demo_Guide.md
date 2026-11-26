# InfraScan &mdash; Final Project Demonstration Script & Presenter Guide

**Project**: InfraScan &mdash; AI-Powered Civil Infrastructure Damage Inspection Platform  
**Target Audience**: Academic Evaluators, Internship Supervisors, Engineering Review Committee  
**Total Target Duration**: ~10–12 Minutes  
**Test Environment**: Local Host (`http://localhost:5173` frontend, `http://localhost:8000` backend, SQLite database)

---

## 1. Demonstration Outline & Timing

| Segment | Topic | Target Time | Presenter Actions | Audience Key Takeaways |
|:---:|---|:---:|---|---|
| **1** | Introduction & Problem Statement | 1.0 min | Title slide / Portal Home | Civil infrastructure aging crisis & manual inspection risks |
| **2** | System Architecture & Tech Stack | 1.5 min | Show Architecture Diagram | FastAPI, React SPA, Docker architecture, deterministic CV |
| **3** | User Registration & Role Guard | 1.0 min | Register page demo | Automated client validation, RBAC privilege escalation guard |
| **4** | User Dashboard & Data Isolation | 1.0 min | User dashboard overview | Multi-tenant isolation, initial zero inspection count |
| **5** | Inspection Upload & Processing | 1.5 min | Upload longitudinal crack photo | Real-time analysis, OpenCV decode guard, background pipeline |
| **6** | Crack Geometry & Severity Engine | 2.0 min | Inspection detail view (#41) | Area, skeleton length, mean aperture (px), rule-based score |
| **7** | Visualizations & Explainable AI | 1.0 min | Toggle Overlay, Mask, Grad-CAM | Multi-model saliency, crack boundaries, focus heatmaps |
| **8** | PDF & CSV Report Export | 1.0 min | Download PDF and CSV | Authenticated ReportLab PDF with overlays & 41-line CSV |
| **9** | Admin Oversight & User Lifecycle | 1.5 min | Admin dashboard & user toggle | System metrics, deactivate/reactivate user, 403 API blocking |
| **10** | Engineering Limitations & Wrap-up | 1.5 min | Model comparison & closing | Pixel proxies, uncalibrated scale, decision support disclaimer |

---

## 2. Detailed Demonstration Walkthrough

### Segment 1: Introduction & Problem Statement (1.0 Min)
* **Screen**: [01_login_page.png](file:///E:/infosys/Internship/InfraScan/docs/screenshots/01_login_page.png) at `http://localhost:5173/login`.
* **Presenter Action**: Open browser to login page. Do not log in immediately.
* **Presenter Narrative**:
  > *"Welcome everyone. Today I am presenting InfraScan, an automated civil infrastructure damage inspection platform. Concrete bridges, highway piers, and tunnel linings suffer from micro-fracturing and deterioration due to environmental cycling and structural fatigue. Traditional visual inspections are slow, subjective, and hazardous. InfraScan provides an objective, automated pipeline that ingests surface inspection photographs, validates image quality, extracts quantitative crack geometry, assesses damage severity, and compiles formal engineering reports while enforcing multi-tenant role-based access control."*
* **Audience Observes**: Modern, dark-themed login portal with branding and authentication security prompts.

---

### Segment 2: System Architecture & Technology Stack (1.5 Min)
* **Screen**: Display [docs/InfraScan_System_Architecture.png](file:///E:/infosys/Internship/InfraScan/docs/InfraScan_System_Architecture.png).
* **Presenter Action**: Walk through the component diagram.
* **Presenter Narrative**:
  > *"Before demonstrating the live application, let's examine the architectural topology. The system is split into three decoupled tiers:
  > 1. **Client Tier**: A responsive React 18 Single Page Application built with Vite and TailwindCSS, managing authentication via React Context.
  > 2. **API & Service Tier**: A high-performance FastAPI backend in Python 3.11/3.13 providing RESTful endpoints, bcrypt password hashing, and 24-hour expiration JWT tokens.
  > 3. **Active Processing Pipeline**: Deterministic computer vision combining Sobel texture classification, bottom-hat mathematical morphology, skeletonization for centerline extraction, and Euclidean distance transforms for aperture calculation.
  > 4. **Persistence Tier**: A persistent Docker volume (`infrascan_data`) retaining SQLite databases, raw inspection uploads, and generated reports across container recreations."*
* **Audience Observes**: Clear distinction between active deterministic processing, persistent storage, and historical experimental models.

---

### Segment 3: User Registration & Role Escalation Defense (1.0 Min)
* **Screen**: Navigate to `http://localhost:5173/register` ([02_registration_page.png](file:///E:/infosys/Internship/InfraScan/docs/screenshots/02_registration_page.png)).
* **Presenter Action**: Fill in registration fields:
  - Username: `demo_inspector_2026`
  - Email: `demo_inspector@infrascan.ai`
  - Full Name: `Field Inspector Demo`
  - Password: `Password123!@#`
  Click **"Create Account"**.
* **Presenter Narrative**:
  > *"Notice our registration flow. Even if a malicious actor intercepts this request via an API client and injects `role: 'admin'`, the FastAPI backend strictly sanitizes the payload, forcing `role: 'user'` on the database layer. Privilege escalation is structurally impossible."*
* **Audience Observes**: Clean account creation, redirection to user dashboard, and immediate authentication.

---

### Segment 4: User Dashboard & Data Isolation (1.0 Min)
* **Screen**: `http://localhost:5173/user/dashboard` ([03_user_dashboard.png](file:///E:/infosys/Internship/InfraScan/docs/screenshots/03_user_dashboard.png)).
* **Presenter Action**: Show top metrics and welcome banner.
* **Presenter Narrative**:
  > *"We are now logged in as a registered inspector. Notice our dashboard isolation: Total Inspections is initially zero. In a multi-tenant civil authority, an inspector in District A cannot see inspections conducted by District B. The navigation bar dynamically adapts to regular user privileges, hiding administrative tools."*
* **Audience Observes**: Clean zero-count state, "Registered Inspector" badge, and empty recent activity list.

---

### Segment 5: Image Upload & Computer Vision Pipeline (1.5 Min)
* **Screen**: Click **"New Inspection"** (`http://localhost:5173/new-inspection`, [04_new_inspection_form.png](file:///E:/infosys/Internship/InfraScan/docs/screenshots/04_new_inspection_form.png)).
* **Presenter Action**:
  - Select Asset: `Pier 14 - Yamuna Expressway Bridge`
  - Upload Image: Select `demo_pier14_longitudinal_crack.jpg`
  - Notes: `Routine quarterly structural audit`
  - Click **"Run Automated Inspection"**.
* **Presenter Narrative**:
  > *"Upon submission, the image passes through our pre-inference security checks: non-image payloads (.exe) are rejected with HTTP 415, and corrupted images are caught by OpenCV decoders with HTTP 400. Once validated, the image undergoes Laplacian blur estimation to verify adequate sharpness, followed by multi-scale bottom-hat morphological filtering to isolate fracture contours from aggregate concrete texture."*
* **Audience Observes**: Processing spinner transitions automatically into the completed inspection detail suite.

---

### Segment 6: Crack Geometry & Severity Engine (2.0 Min)
* **Screen**: Inspection Detail Page ([06_inspection_detail_overview.png](file:///E:/infosys/Internship/InfraScan/docs/screenshots/06_inspection_detail_overview.png) and [07_crack_geometry_severity.png](file:///E:/infosys/Internship/InfraScan/docs/screenshots/07_crack_geometry_severity.png)).
* **Presenter Action**: Scroll down to the **"Crack Geometry & Quantitative Extraction"** and **"Severity Assessment"** cards.
* **Presenter Narrative**:
  > *"Here is the quantitative analysis extracted from the crack:
  > - **Total Defect Area**: 9,496 px (3.62% surface coverage).
  > - **Skeleton Axis Length**: 2,845 px along the medial thinned centerline.
  > - **Mean Aperture Width**: 3.3 px, with maximum aperture reaching 9.6 px.
  > - **Topology**: 12 distinct branch junctions and 4 interconnected segments.
  >
  > Next, our rule-based severity engine calculates a composite score:
  > - Base crack score: 20.0
  > - Density score (>2.0% coverage): +40.0
  > - Aperture width score (max < 10px): +5.0
  > - Topology score (>10 branches): +15.0
  > Total Score: **80.0 / 100 &mdash; Severe Damage (Urgent Review Required)**.
  > The system immediately outputs an actionable maintenance directive: 'Schedule specialized non-destructive testing and epoxy injection sealing within 14 days.'"*
* **Audience Observes**: Color-coded severity badges, structured geometry metrics, and transparent mathematical rationale.

---

### Segment 7: Visualizations & Explainable AI (1.0 Min)
* **Screen**: Image Visualization Pane ([08_gradcam_overlay.png](file:///E:/infosys/Internship/InfraScan/docs/screenshots/08_gradcam_overlay.png)).
* **Presenter Action**: Click between tabs: **Segmentation Overlay** &rarr; **Grad-CAM Saliency** &rarr; **Binary Mask** &rarr; **Raw Image**.
* **Presenter Narrative**:
  > *"Engineers must trust AI results. By clicking 'Grad-CAM Saliency', we visualize the convolutional activation heatmap, confirming that the model focused directly on the fissure rather than background shadows or formwork joints. Clicking 'Binary Mask' shows the clean skeleton input used for geometry calculations."*
* **Audience Observes**: Instant interactive tab switching between segmented boundary overlays, heatmap activation, and raw photography.

---

### Segment 8: PDF & CSV Report Generation (1.0 Min)
* **Screen**: Click **"Download PDF Report"** and **"CSV Data"** buttons ([16_pdf_report.png](file:///E:/infosys/Internship/InfraScan/docs/screenshots/16_pdf_report.png) and [17_csv_report_preview.png](file:///E:/infosys/Internship/InfraScan/docs/screenshots/17_csv_report_preview.png)).
* **Presenter Action**: Open the downloaded PDF in the browser or viewer.
* **Presenter Narrative**:
  > *"Civil engineers require legally compliant audit artifacts. Using ReportLab, InfraScan generates a formal binary PDF report containing complete asset metadata, quantitative geometry tables, high-resolution visual overlays, and our mandatory structural disclaimer. For machine ingestion, the CSV export outputs 41 standardized rows suitable for GIS or asset management databases."*
* **Audience Observes**: Professional multi-page PDF document and structured CSV tabular data.

---

### Segment 9: Administrator Dashboard & Account Lifecycle (1.5 Min)
* **Screen**: Click **"Sign Out"**, then log in as `admin` (`http://localhost:5173/admin/dashboard`, [10_admin_dashboard.png](file:///E:/infosys/Internship/InfraScan/docs/screenshots/10_admin_dashboard.png)).
* **Presenter Action**:
  - Show System Overview: 15 registered users, 46 inspections across the entire authority.
  - Click **"User Management"** tab ([11_admin_user_management.png](file:///E:/infosys/Internship/InfraScan/docs/screenshots/11_admin_user_management.png)).
  - Click **"Deactivate"** on a test inspector account. Show that status flips to 'inactive'.
  - Click **"Reactivate"** to restore account privileges.
  - Click **"All Inspections"** tab ([12_admin_system_inspections.png](file:///E:/infosys/Internship/InfraScan/docs/screenshots/12_admin_system_inspections.png)).
* **Presenter Narrative**:
  > *"Switching to Administrator view, we see executive oversight across all users and bridge assets. Notice the user management panel: administrators can immediately revoke access for offboarded inspectors. When deactivated, that user is blocked from logging in with HTTP 403 and cannot query existing inspection records."*
* **Audience Observes**: Instant real-time user status toggling, cross-tenant inspection auditing, and administrative metrics.

---

### Segment 10: Academic Truth, Limitations & Wrap-Up (1.5 Min)
* **Screen**: Click **"Model Evaluation"** (`http://localhost:5173/models`, [09_model_comparison.png](file:///E:/infosys/Internship/InfraScan/docs/screenshots/09_model_comparison.png)).
* **Presenter Action**: Highlight the provenance table and limitations notice.
* **Presenter Narrative**:
  > *"In concluding this demonstration, we emphasize academic truth in reporting:
  > 1. **Pixel vs. Metric**: All measurements are reported in pixel space. Without laser targets or calibrated focal parameters, pixel measurements cannot be claimed as millimeters.
  > 2. **Decision Support**: The severity engine is a rule-based preliminary triage tool, not a certified legal structural health determination.
  > 3. **Model Provenance**: Our active local YOLO checkpoint is the 80-class COCO baseline, which our detector strictly isolates from crack geometry. Historical deep-learning benchmarks (CNN 99.69% accuracy, U-Net 54.08% IoU) are documented for academic research but correctly labeled as offline experiments.
  >
  > InfraScan delivers a secure, reproducible, container-ready civil inspection platform with 100% verified integration tests."*
* **Audience Observes**: Professional, honest academic disclosure aligned with software engineering best practices.

---

## 3. Presenter Preparation Checklist
- [x] Backend running on `http://localhost:8000`.
- [x] Frontend running on `http://localhost:5173`.
- [x] Database `infrascan.db` verified with active asset records.
- [x] Test credentials ready: `admin` and `int_user_1795371513` (`ComplexPass123!@#`).
- [x] Example image available: `demo_pier14_longitudinal_crack.jpg`.
