# InfraScan Milestone 3 & Milestone 4 Ground Truth Facts

**Generated Date**: 2026-11-25  
**Scope**: Verification and fact-checking of all Milestone 3 (Weeks 5-6) and Milestone 4 (Weeks 7-8) deliverables.  
**Author**: Shree Nidhi Pradeep (`shreenidhipradeep2006@gmail.com`)  
**Repository**: `D:\Infosys springboards\infrascan\`  

---

## 1. Summary of Verification Status

| Milestone | Category | Total Items | IMPLEMENTED | PARTLY | NOT IMPLEMENTED | COULD NOT VERIFY |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Milestone 3** | Advanced Models & Defect Detection | 6 | 3 | 1 | 2 | 0 |
| **Milestone 3** | Crack Geometry Analysis | 5 | 5 | 0 | 0 | 0 |
| **Milestone 3** | Damage Severity & Prioritization | 4 | 4 | 0 | 0 | 0 |
| **Milestone 3** | Historical Comparison | 3 | 3 | 0 | 0 | 0 |
| **Milestone 3** | Explainable AI (XAI) | 4 | 4 | 0 | 0 | 0 |
| **Milestone 4** | Frontend Multi-Role Dashboard | 8 | 8 | 0 | 0 | 0 |
| **Milestone 4** | Real-Time WebSocket Architecture | 5 | 5 | 0 | 0 | 0 |
| **Milestone 4** | Production Hardening & Database | 6 | 6 | 0 | 0 | 0 |
| **Milestone 4** | Maintenance Ticketing & SLA | 4 | 4 | 0 | 0 | 0 |
| **Milestone 4** | PDF Report Generation | 3 | 3 | 0 | 0 | 0 |
| **Milestone 4** | Optimization & Performance | 4 | 4 | 0 | 0 | 0 |
| **Milestone 4** | Docker & Deployment | 3 | 2 | 0 | 0 | 1 |
| **Milestone 4** | Testing & Quality Assurance | 4 | 4 | 0 | 0 | 0 |
| **TOTAL** | | **59** | **51** | **1** | **6** | **1** |

---

## 2. Milestone 3: Detailed Ground Truth Items (Weeks 5-6)

### 2.1 Advanced Models Evaluated
- **YOLOv8s vs YOLO11s (Road Damage Detection - RDD2022)**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `infrascan/ml/experiments/`, `docs/11_milestone2_results.md`, `docs/12_model_evaluation_report.md`.
  - **Key Numbers**: Trained on 8,000 small subset of RDD2022.
    - YOLOv8s [VALIDATION]: Best mAP@50 = `0.4554`, mAP@50:95 = `0.2220`, Precision = `0.5211`, Recall = `0.4528`.
    - YOLO11s [VALIDATION]: Best mAP@50 = `0.4437`, mAP@50:95 = `0.2151`.
    - Selection: YOLOv8s selected based on mAP@50:95 validation superiority rule.
    - Plan Target ($\text{mAP@50} \ge 0.85$, $\text{Recall} \ge 0.90$): NOT REACHED on validation.
  - **Limitation**: TEST SPLIT NOT EVALUATED because RDD2022 test split is unannotated by dataset publishers.

- **RT-DETR-L (Multi-Class Defect Detection - CODEBRIM)**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `infrascan/backend/app/services/defect_detector.py`, `docs/13_codebrim_preparation.md`, `docs/12_model_evaluation_report.md`.
  - **Key Numbers**:
    - Dataset: CODEBRIM, 1,022 processed images, 5 defect classes (`crack`, `spallation`, `exposed_bars`, `efflorescence`, `corrosion_stain`), 8,274 bounding boxes. Non-commercial academic license.
    - Model: RT-DETR-L (`A2_rtdetr_l`).
    - Validation Metrics [VALIDATION]: mAP@50 = `0.4120`, mAP@50:95 = `0.2480`.
  - **Limitation**: TEST SPLIT NOT EVALUATED (held out without local labels).

- **ConvNeXt & Swin Transformer (Classification)**:
  - **Status**: `NOT IMPLEMENTED`
  - **Evidence**: `docs/12_model_evaluation_report.md` (Sections 2 & 10).
  - **Exact Reason**: Planned in early architecture exploration, but not trained or evaluated. Compute and time budgets were allocated to high-resolution U-Net++ segmentation and object detection (YOLOv8s & RT-DETR-L); ResNet-50 was selected as the verified classification baseline.

- **SegFormer & EfficientNet (Segmentation)**:
  - **Status**: `NOT IMPLEMENTED`
  - **Evidence**: `docs/12_model_evaluation_report.md` (Sections 4 & 10).
  - **Exact Reason**: ResNet-34 U-Net and U-Net++ were selected and rigorously benchmarked on Crack500 and CFD. SegFormer and EfficientNet variants were not trained as U-Net++ achieved stable convergence and met production latency targets.

- **U-Net++ vs Standard U-Net (Crack Segmentation - Crack500 & CFD)**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `docs/11_milestone2_results.md`, `docs/12_model_evaluation_report.md`, `infrascan/backend/app/services/segmentation.py`.
  - **Key Numbers**: Winner: `unetplusplus_crack500` (threshold = 0.40).
    - Crack500 Clean TEST (N=1,087): Mean Dice = `0.6899` [95% CI: 0.6801, 0.7001], Mean IoU = `0.5481` [0.5382, 0.5586], Pixel Dice = `0.7309`, Pixel IoU = `0.5759`, Boundary F1 (3px) = `0.4523` [TEST]. Plan target ($\text{Dice} \ge 0.85$, $\text{IoU} \ge 0.75$) NOT REACHED.
    - CFD Zero-Shot Generalization TEST (N=118): Mean Dice = `0.4533`, Mean IoU = `0.3109` [TEST]. Demonstrates cross-domain distribution shift.

- **Concrete Crack Classification Baselines (CCIC & SDNET2018)**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `docs/11_milestone2_results.md`, `docs/12_model_evaluation_report.md`.
  - **Key Numbers**:
    - CCIC TEST (N=5,760, threshold 0.4951): Macro F1 = `0.9997` [TEST, Plan target $\ge 0.85$ REACHED]. Near-duplicate audit revealed 931 duplicates (16.16% at dHash $\le 2$); on 4,829 unique images F1 = `0.9995`. Best epoch = 13.
    - SDNET2018 TEST (N=8,802, threshold 0.0100 for val recall $\ge 0.90$): Macro F1 = `0.6421` [TEST, Plan target $\ge 0.85$ NOT REACHED due to low precision 0.3247 and 2,429 false positives]. Severe background texture overfitting observed after Epoch 7.

---

### 2.2 Crack Geometry Analysis
- **Medial Axis Skeletonization & Medial Path**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `infrascan/backend/app/services/crack_geometry.py`, `backend/tests/test_crack_geometry.py`.
  - **Implementation**: Uses `skimage.morphology.medial_axis` to extract the 1-pixel centerline of segmented cracks.
- **Crack Width via Euclidean Distance Transform (EDT2)**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `infrascan/backend/app/services/crack_geometry.py` (`calculate_geometry`), `backend/tests/test_crack_geometry.py`.
  - **Implementation**: Computes `scipy.ndimage.distance_transform_edt` on binary mask. Width along skeleton equals $2 \times \text{EDT}$. Evaluates max width, mean width, and standard deviation.
- **Crack Orientation, Endpoints, and Branching Detection**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `infrascan/backend/app/services/crack_geometry.py`.
  - **Implementation**: Cross-correlation 8-connectivity kernel: branch points defined by $\ge 3$ neighbors; endpoints defined by exactly 1 neighbor. Principal orientation derived via eigenvector decomposition of skeleton coordinates.
- **Scale Calibration Tool**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `infrascan/backend/app/services/scale.py`, `infrascan/frontend/src/pages/InspectionDetail.tsx`.
  - **Implementation**: Reference marker calibration tool (`calibrate_scale(pixel_distance, known_mm)`).
- **Physical Units & Measurement Uncertainty**:
  - **Status**: `IMPLEMENTED`
  - **Rule**: Measurements are reported in **pixels** by default. Converted to **millimeters only when a calibrated scale is stored**.
  - **Key Numbers**: Discrete spatial quantization error and skeleton edge uncertainty are calculated as $\pm 4.7\text{ px}$ ($\pm 7\text{ mm}$ at nominal $1.5\text{ mm/px}$ scale).

---

### 2.3 Damage Severity Assessment
- **4-Level Severity Scale**:
  - **Status**: `IMPLEMENTED`
  - **Scale**: `low` (1), `medium` (2), `high` (3), `critical` (4).
- **Severity Rule Engine & Config**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `infrascan/backend/app/config/severity_rules.json` (v1.0, marked "engineer-defined placeholders"), `infrascan/backend/app/services/severity.py`.
  - **Factors**:
    - Factor A: Crack density % (up to 40 pts)
    - Factor B: Relative crack length % (up to 20 pts)
    - Factor C: Branching complexity (up to 8 pts)
    - Factor D: Damage type weighting (up to 40 pts)
    - Factor E: Damage area share % (up to 15 pts)
    - Factor F: Calibrated crack width in mm (up to 20 pts; 0 if uncalibrated)
- **Safety Overrides**:
  - **Status**: `IMPLEMENTED`
  - **Implementation**: Forced minimum severity: any detected `exposed_bars` triggers minimum severity `critical` (4); detected large `spallation` triggers minimum severity `high` (3).
- **Rule Stability Verification**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `docs/14_severity_rules.md` (Section 4).
  - **Key Numbers** (Evaluated across 1,087 Crack500 test images):
    - Exact agreement across perturbation: `77.09%`
    - Agreement within 1 level: `99.08%`
    - Quadratic Weighted Kappa: $\kappa = 0.7542$ (substantial inter-test stability).

---

### 2.4 Historical Image Comparison
- **Image Registration & Alignment**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `infrascan/backend/app/services/historical_comparison.py`, `backend/tests/test_historical_comparison.py`.
  - **Algorithm**: ORB feature matching + RANSAC homography estimation (`cv2.findHomography` with `cv2.RANSAC`).
- **Non-Comparable Rejection Safeguard**:
  - **Status**: `IMPLEMENTED`
  - **Implementation**: Rejects registration if inlier count $< 15$ or perspective scale change $> 2.0\times$. Sets `is_comparable=False` with descriptive reason.
- **Crack Growth Tracking & Difference Heatmap**:
  - **Status**: `IMPLEMENTED`
  - **Implementation**: Computes warp alignment, difference mask, percentage area growth, and delta maximum width between successive inspections.

---

### 2.5 Explainable AI (XAI)
- **Attribution Methods Supported**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `infrascan/backend/app/services/xai.py`, `docs/15_explainable_ai.md`, `backend/tests/test_xai.py`.
  - **Methods**: Grad-CAM, Grad-CAM++, Captum Saliency / Integrated Gradients, and EigenCAM.
  - **Target Layers**:
    - U-Net++: `model.encoder.layer4[-1]`
    - YOLOv8s: `model.model.model[21]`
    - RT-DETR-L: `model.model.model[27]`
    - ResNet-50: `model.layer4[-1]`
- **Sanity Check: Parameter Randomization (Adebayo Test)**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `docs/15_explainable_ai.md` (Table 4, N=50 Crack500 validation images).
  - **Key Numbers**: Spearman rank correlation between trained and randomized weights drops to $r = 0.1069$ (Grad-CAM) and $r = -0.1685$ (Grad-CAM++), passing the Adebayo weight-sensitivity check.
- **Sanity Check: Feature Deletion Test**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `docs/15_explainable_ai.md` (Table 5).
  - **Key Numbers**: Masking top 10% attribution pixels causes segmentation Mean Dice drop $\Delta\text{Dice} = 0.0656$ vs random pixel masking drop $0.0252$ (2.61x selective impairment ratio).

---

## 3. Milestone 4: Detailed Ground Truth Items (Weeks 7-8)

### 3.1 Frontend Multi-Role Dashboard
- **Role-Based Views & Authorization**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `infrascan/frontend/src/config/role_permissions.json`, `infrascan/frontend/src/components/ProtectedRoute.tsx`.
  - **Roles**: `admin`, `civil_engineer`, `inspector`, `manager`, `maintenance_engineer`. Route-level enforcement verified across all 15 application routes.
- **Interactive Geospatial Map**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `infrascan/frontend/src/pages/Map.tsx`.
  - **Features**: Leaflet map, marker clustering, asset health recoloring (Critical=Red, High=Orange, Medium=Yellow, Low=Green, Uninspected=Gray), asset detail popups.
- **Inspection Detail & Crack Geometry Overlay**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `infrascan/frontend/src/pages/InspectionDetail.tsx`, `infrascan/frontend/src/components/GeometryOverlay.tsx`.
  - **Visualizations**: Interactive SVG canvas displaying crack skeleton (green), width normals (magenta), branch points (orange diamonds), endpoints (blue circles), and bounding boxes.
- **Maintenance Ticket Management Kanban & Table**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `infrascan/frontend/src/pages/Maintenance.tsx`.
  - **Features**: Status columns, priority badges, assigned engineer, SLA deadline counter, transition actions.
- **PDF Report Direct Download**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `infrascan/frontend/src/pages/Reports.tsx`, `InspectionDetail.tsx`.
  - **Endpoint**: `GET /api/v1/reports/inspections/:id/pdf`.
- **Accessibility & WCAG AA Compliance**:
  - **Status**: `IMPLEMENTED`
  - **Audit**: Verified 4.5:1 minimum text contrast ratio, screen-reader `aria-label` tags on icon buttons, keyboard focus rings (`focus-visible:ring-2 focus-visible:ring-primary-500`).
- **Dark/Light Theme & Keyboard Shortcuts**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `infrascan/frontend/src/components/ThemeToggle.tsx`, `infrascan/frontend/src/hooks/useKeyboardShortcuts.ts`.
  - **Shortcuts**: `?` opens modal, `g d` dashboard, `g m` map, `g i` inspections, `g t` maintenance, `g r` reports.

---

### 3.2 Real-Time Architecture & Messaging
- **WebSocket Hub with Topic-Based Pub/Sub**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `infrascan/backend/app/services/websocket_manager.py`, `frontend/src/services/websocket.ts`.
  - **Channels**: `notifications:{user_id}`, `inspections`, `tickets`, `system`.
- **Heartbeat & Dead Connection Pruning**:
  - **Status**: `IMPLEMENTED`
  - **Details**: 30-second ping/pong cycles. Stale client connections purged automatically.
- **Reconnection with Exponential Backoff**:
  - **Status**: `IMPLEMENTED`
  - **Intervals**: 1s, 2s, 4s, 8s up to 30s max backoff in `frontend/src/services/websocket.ts`.
- **Redis Streams / PubSub with In-Memory Fallback**:
  - **Status**: `IMPLEMENTED`
  - **Details**: Redis PubSub used for horizontal multi-worker scaling; automatic in-memory broadcast fallback when Redis is absent.
- **Concurrent Multi-User Isolation**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: 11 multi-user Playwright acceptance scenarios verified; user-scoped notifications never leak across sessions.

---

### 3.3 Production Hardening & Database
- **PostgreSQL 16 Schema & Indexing**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: 32 relational tables in `infrascan/backend/app/models/`.
  - **Indexes**: Spatial index `idx_assets_location_gist`, composite index `idx_notifications_user_unread`, `idx_inspections_asset_date`.
- **Database Query Latency Benchmarks (EXPLAIN ANALYZE)**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `docs/final/performance_report.md` (Section 3).
  - **Key Numbers**:
    - Spatial asset query: `4.2 ms` $\to$ `0.12 ms` (**35x speedup** with GiST index).
    - Unread notifications query: `8.1 ms` $\to$ `0.18 ms` (**45x speedup** with composite index).
- **Connection Pooling & Migrations**:
  - **Status**: `IMPLEMENTED`
  - **Config**: SQLAlchemy `QueuePool` with pool size = 10, max overflow = 20, recycle = 1800s. 11 idempotent migration scripts in `infrascan/scripts/migrations/`.
- **Health Probes**:
  - **Status**: `IMPLEMENTED`
  - **Endpoints**: `/healthz` (liveness), `/readyz` (readiness with DB and Redis ping), `/livez`.
- **API Rate Limiting & Security Hardening**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `slowapi` Limiter (60 req/min general, 10 req/min auth), CORS origin whitelist, security headers.
- **Audit Logging Engine**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `infrascan/backend/app/models/audit.py`, `infrascan/backend/app/services/audit.py`, `infrascan/frontend/src/pages/AuditLogs.tsx`.
  - **Fields**: Immutable audit trail recording user ID, action, entity type, entity ID, client IP, timestamp, and JSON diff.

---

### 3.4 Maintenance Prioritization & Ticketing
- **Priority Calculation Matrix**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `infrascan/backend/app/services/maintenance_prioritization.py`, `infrascan/backend/app/models/maintenance.py`.
  - **Formula**: Calculated from Severity (1-4) $\times$ Urgency (1-4) $\to$ P1, P2, P3, P4.
- **SLA Deadline Thresholds**:
  - **Status**: `IMPLEMENTED`
  - **Tiers**:
    - **P1 (Critical)**: 24 hours SLA
    - **P2 (High)**: 7 days (168 hours) SLA
    - **P3 (Medium)**: 30 days (720 hours) SLA
    - **P4 (Low)**: 90 days (2,160 hours) SLA
- **Ticket State Machine**:
  - **Status**: `IMPLEMENTED`
  - **Transitions**: `open` $\to$ `in_progress` $\to$ `under_review` $\to$ `resolved` $\to$ `closed`. Strict validation prevents invalid state jumps.
- **Real-Time Ticket Dispatch**:
  - **Status**: `IMPLEMENTED`
  - **Details**: Assignments and state changes trigger live WebSocket messages and notification records.

---

### 3.5 PDF Report Generation
- **ReportLab PDF Engine**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `infrascan/backend/app/services/pdf_generator.py`, `backend/tests/test_pdf.py`. ReportLab version `5.1.0`.
- **Layout & Visual Styling**:
  - **Status**: `IMPLEMENTED`
  - **Design**: Professional corporate palette: Deep navy headers (`#1e3a8a`), slate secondary (`#475569`), zebra-striped measurement tables (`#f8fafc`).
- **Required Report Elements**:
  - **Status**: `IMPLEMENTED`
  - **Contents**: Asset metadata, inspection ID, crack geometric metrics, severity factor breakdown, crack mask visual overlay, historical comparison change metric, qualified engineer signature block.
- **Mandatory Disclaimers Included**:
  - **Status**: `IMPLEMENTED`
  - *\"AI result for engineer review, not a final structural safety verdict.\"*
  - *\"No damage detected by the AI. This is not evidence that there is no damage.\"*

---

### 3.6 Performance Optimization
- **Inference Latency & Resolution Scaling**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `docs/final/performance_report.md` (Section 1).
  - **Key Numbers**:
    - YOLOv8s at 640px: `170.05 ms` (peak RAM 1.2 MB); at 1280px: `733.92 ms`.
    - U-Net++ at 640px: `354.76 ms`; at 1280px: `391.73 ms`.
    - Dynamic downscaling to max 1280px reduces peak GPU memory by **72%** while resulting in negligible segmentation loss ($\Delta\text{IoU} = -0.0018$ / -0.33%).
    - Half precision FP16 inference yields **1.85x** throughput gain on CUDA hardware.
- **Frontend Bundle Optimization**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `infrascan/frontend/vite.config.ts`. Dynamic route-level code splitting using `React.lazy()`. Production build finishes in `1.48s - 3.85s` with vendor chunk isolation.
- **Database Query Latency Optimization**:
  - **Status**: `IMPLEMENTED`
  - **Key Numbers**: 35x speedup on spatial lookups; 45x speedup on unread notifications.

---

### 3.7 Deployment & Docker Configuration
- **Multi-Stage Dockerfiles**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `infrascan/deploy/Dockerfile.backend` (multi-stage `python:3.11-slim`, non-root user `appuser`, health check probe), `infrascan/deploy/Dockerfile.frontend` (multi-stage Node 20 build + Nginx Alpine runtime).
- **Docker Compose Orchestration**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `infrascan/deploy/docker-compose.yml`. Configures 5 services: `backend`, `worker`, `frontend`, `db` (PostgreSQL 16), `redis` (Redis 7).
- **Security & Secret Isolation**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `infrascan/deploy/.env.example` contains zero hardcoded secrets. Non-root user privileges.
- **Docker Daemon Live Container Runtime**:
  - **Status**: `COULD NOT VERIFY`
  - **Limitation**: The local Windows development machine does not have the Docker Desktop daemon service running. Compose configuration and Dockerfiles were statically validated, and native backend/frontend services verified live.

---

### 3.8 Testing & Quality Assurance
- **Backend Test Suite**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `pytest -p no:cacheprovider -q`.
  - **Key Numbers**: **126 / 126 PASSED** (100% pass rate in 216.80 seconds).
- **Frontend Static Analysis & Type Checking**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `npx oxlint` finished in 1.4s with **0 errors** (50 warnings); `npx tsc -b` completed with **0 errors**.
- **End-to-End Multi-Role Acceptance Testing**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `docs/final/realtime_test_report.md`. **11 / 11 scenarios passed** across all 5 user roles; 10 evidence screenshots captured in `docs/final/realtime_screens/`.
- **System Load & Concurrency Benchmark**:
  - **Status**: `IMPLEMENTED`
  - **Evidence**: `docs/final/performance_report.md` (evaluated under 100 concurrent virtual users; peak response time $< 250\text{ ms}$ for cached API endpoints).

---

## 4. Figures and Visual Artifacts Catalog

The following figures are available on disk in `docs/` and ready for embedding into Milestone 3 and Milestone 4 documentation:

| Figure File | Size | Suitable Section | Description / Caption |
| :--- | :---: | :--- | :--- |
| `docs/figures/concrete_crack_confusion_matrix.png` | 86.2 KB | M3: Classification | CCIC concrete crack classification test confusion matrix ($F_1=0.9997$). |
| `docs/figures/concrete_crack_pr_curve.png` | 67.6 KB | M3: Classification | Precision-Recall curve for CCIC crack classification. |
| `docs/figures/concrete_crack_roc_curve.png` | 94.5 KB | M3: Classification | ROC curve with AUC metric for CCIC model. |
| `docs/figures/concrete_crack_training_curves.png` | 120.3 KB | M3: Classification | Training loss and validation accuracy curves for ResNet-50 on CCIC. |
| `docs/figures/sdnet2018_confusion_matrix.png` | 91.0 KB | M3: Classification | SDNET2018 test confusion matrix illustrating false positive rate ($F_1=0.6421$). |
| `docs/figures/sdnet2018_group_metrics.png` | 63.4 KB | M3: Classification | Subgroup performance across bridge deck, wall, and pavement sub-classes. |
| `docs/figures/sdnet2018_training_curves.png` | 130.9 KB | M3: Classification | SDNET2018 training curves exhibiting validation loss divergence after epoch 7. |
| `docs/figures/yolov8s_BoxPR_curve.png` | 198.2 KB | M3: Detection | YOLOv8s Precision-Recall curve on RDD2022 road damage validation split. |
| `docs/figures/yolov8s_confusion_matrix.png` | 153.0 KB | M3: Detection | Normalized confusion matrix for YOLOv8s multi-defect detection. |
| `docs/figures/yolov8s_results.png` | 269.0 KB | M3: Detection | Metric trajectories across 50 epochs for YOLOv8s training. |
| `docs/figures/codebrim_yolo_samples.jpg` | 614.5 KB | M3: Defect Detection | Ground truth bounding boxes for CODEBRIM multi-class bridge defects. |
| `docs/figures/crack500_panel_best_01.png` | 971.7 KB | M3: Segmentation | U-Net++ best-case segmentation visual comparison on Crack500 test image. |
| `docs/figures/crack500_panel_median_01.png` | 1.22 MB | M3: Segmentation | U-Net++ median-case segmentation comparison showing thin crack continuity. |
| `docs/figures/crack500_panel_worst_01.png` | 889.2 KB | M3: Segmentation | U-Net++ worst-case segmentation panel illustrating shadow false positive. |
| `docs/figures/crack500_thickness_results.png` | 57.0 KB | M3: Geometry | Crack width distribution and thickness quantification on Crack500. |
| `docs/figures/cfd_example_panels_summary.png` | 1.91 MB | M3: Segmentation | Zero-shot cross-dataset evaluation of Crack500-trained U-Net++ on CFD dataset. |
| `docs/figures/cfd_thickness_results.png` | 54.7 KB | M3: Geometry | Thickness profile and width normal estimates on CFD dataset. |
| `docs/figures/geometry_overlay_01.png` | 452.9 KB | M3: Geometry | Extracted medial axis skeleton, branch points, and endpoints on crack mask. |
| `docs/figures/geometry_overlay_04.png` | 430.0 KB | M3: Geometry | Normal width measurement vectors along crack skeleton path. |
| `docs/final/screenshots/01_dashboard.png` | 11.5 KB | M4: Dashboard | Overview of executive engineering dashboard and high-level health cards. |
| `docs/final/screenshots/02_map.png` | 11.5 KB | M4: Geospatial Map | Interactive GIS asset map with clustered infrastructure condition markers. |
| `docs/final/screenshots/03_models.png` | 30.9 KB | M4: AI Monitoring | Production AI model registry and inference monitoring console. |
| `docs/final/screenshots/04_jobs.png` | 16.4 KB | M4: Background Processing | Background inspection batch processing and async task queue monitor. |
| `docs/final/screenshots/05_reports.png` | 12.5 KB | M4: Reporting | PDF report generation interface with asset filters and download buttons. |
| `docs/final/screenshots/06_notifications.png` | 11.8 KB | M4: Real-Time | Real-time user notification inbox with priority alert styling. |
| `docs/final/realtime_screens/01_inspector_assignment_live.png` | 70.7 KB | M4: Workflows | Real-time inspector assignment push notification and queue update. |
| `docs/final/realtime_screens/02_analysis_progress_live.png` | 38.5 KB | M4: Workflows | Live WebSocket progress bar for asynchronous deep learning inference. |
| `docs/final/realtime_screens/03_civil_engineer_review_live.png` | 76.2 KB | M4: Workflows | Civil engineer review portal with geometry inspector and verification tools. |
| `docs/final/realtime_screens/04_manager_map_recolor_live.png` | 395.8 KB | M4: Workflows | Live map recoloring to critical red upon engineer verdict confirmation. |
| `docs/final/realtime_screens/05_maintenance_task_live.png` | 52.3 KB | M4: Workflows | P1 maintenance work order dispatched live to maintenance engineer. |
| `docs/final/realtime_screens/06_task_completion_live.png` | 80.8 KB | M4: Workflows | Maintenance task resolution updating asset health status in real time. |
| `docs/final/realtime_screens/07_report_ready_live.png` | 396.1 KB | M4: Workflows | Automated generation notification and live download of engineering PDF. |
| `docs/final/realtime_screens/08_session_revoked_logout.png` | 20.4 KB | M4: Security | Real-time session revocation forcing immediate logout across tabs. |
| `docs/final/realtime_screens/09_polling_fallback_live.png` | 80.9 KB | M4: Resilience | Graceful degradation to HTTP long-polling upon WebSocket interruption. |
| `docs/final/realtime_screens/10_multitab_sync.png` | 73.3 KB | M4: Real-Time | Multi-tab state synchronization via shared broadcast channel. |

---

## 5. Limitations, Non-Trained Models, and Unverified Items

1. **Non-Trained Advanced Architectures**:
   - `ConvNeXt` and `Swin Transformer`: Not trained or evaluated. ResNet-50 was utilized as the primary verified classification architecture.
   - `SegFormer` and `EfficientNet`: Not trained or evaluated. ResNet-34 U-Net and U-Net++ were selected as the dense segmentation models.
2. **Unannotated Test Splits**:
   - `RDD2022`: The official test split has unreleased ground-truth labels. Therefore, all reported object detection metrics for YOLOv8s and YOLO11s are strictly **VALIDATION** metrics.
   - `CODEBRIM`: Multi-class defect detection with RT-DETR-L was evaluated on the local validation split; the test split was held out without labels.
3. **Environment & Host Constraints**:
   - `Docker Daemon Runtime`: The Docker daemon was not running on the host machine. The Dockerfiles and `docker-compose.yml` configurations were statically validated, but live container startup could not be executed. Native services (FastAPI, React Vite, PostgreSQL) were verified live.
4. **Data Attribution**:
   - Dashboard asset data, simulated high-volume load test data, and demo tickets are explicitly identified as **DEMO DATA (synthetic)**.
