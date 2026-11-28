# InfraScan 🏗️
**AI-Powered Civil Infrastructure Crack & Damage Assessment Platform**

> ⚠️ **Civil Engineering Decision Support Notice**: InfraScan is an AI-powered visual screening and decision-support system designed to assist civil engineers, inspectors, and infrastructure authorities. AI-derived measurements and damage severity classifications are non-destructive screening assessments and must not substitute for certified professional engineering inspections or official physical structural safety certifications.

---

## System Overview

InfraScan is an end-to-end, enterprise-grade AI civil engineering platform designed to inspect, detect, segment, classify, quantify, and track defects across bridges, dams, highways, tunnels, retaining walls, and concrete buildings. 

It fuses state-of-the-art computer vision (MobileNetV3-TTA, YOLOv8 bounding boxes, U-Net pixel segmentation, morphological skeletonization, Grad-CAM/Grad-CAM++/Saliency explainability) with real-world physical calibration, maintenance workflow automation, GIS geospatial mapping, and automated engineering report exports.

### Core Architectural Highlights
- **94.60% Defect Classification Accuracy**: Validated against composite multi-domain infrastructure benchmarks (SDNET2018 bridge decks/walls/pavements + METU concrete benchmark) using 8-view test-time augmentation (TTA).
- **Sub-50ms Inference Latency**: Optimized ONNX Runtime execution engine suitable for low-power edge field laptops and smartphones.
- **Physical Millimeter Calibration**: Converts pixel coordinates to real-world metric dimensions ($mm$, $mm^2$, $mm/px$) with dynamic calibration override.
- **8-Class Crack Morphology Engine**: Longitudinal, Transverse, Diagonal, Vertical, Horizontal, Alligator/Map Cracking, Hairline, and Random/Irregular.
- **9-Class Multi-Defect Detection**: Concrete Spalling, Surface Corrosion, Exposed Rebar, Potholes, Surface Deformation, Delamination, Water Staining/Leakage, Material Erosion, and Structural Cracks.
- **Explainable AI (XAI)**: Grad-CAM, Grad-CAM++ (multi-defect instance gradient weighting), and raw input pixel Saliency maps.
- **Multi-Format Engineering Reporting**: One-click generation of professional ReportLab PDF reports (with engineer signoff block), CSV spreadsheets, Excel workbooks (.xlsx with openpyxl), and structured JSON exports.
- **GIS Defect Mapping**: Interactive Leaflet & OpenStreetMap geospatial clustering and risk prioritization.
- **Time-Series Damage Progression**: Comparative inspection analysis calculating millimeter expansion deltas, deterioration velocity, and emerging defects.
- **Maintenance Prioritization & Work Orders**: Automated risk scoring (0–100) driving an integrated work order ticketing system.
- **Containerized Orchestration**: Production-ready multi-container Docker Compose setup (PostgreSQL, FastAPI backend, Nginx React frontend).

---

## 22-Module Functional Architecture

The platform implements all 22 modules structured across 4 engineering milestones:

### Milestone 1: Core Foundation & Data Pipeline
1. **User Authentication & Role-Based Access Control (RBAC)**: Secure JWT access tokens, bcrypt password hashing, and role-guarded endpoints across 5 engineering tiers (Civil Engineer, Infrastructure Inspector, Maintenance Engineer, Infrastructure Manager, Administrator).
2. **Infrastructure Asset & Inspection Management**: Asset registry with engineering specifications (construction year, material composition, department, inspection frequency), GPS benchmarks, and historical inspection tracking.
3. **Image Capture & Upload Module**: Supports field camera capture with live viewfinder, rotation/cropping tools, high-resolution drone uploads, and batch uploads.
4. **Image Validation Engine**: Multi-stage validation detecting corrupt files, unsupported MIME formats, tiny dimensions (<64x64), motion blur (Laplacian variance), low-light/overexposure, and SHA-256 duplicate image rejection.
5. **Image Preprocessing Engine**: 7-stage image filter pipeline: CLAHE contrast enhancement, unsharp mask sharpening, shadow reduction & division normalization, Canny/Sobel edge enhancement, concrete texture accentuation, ROI isolation, and ImageNet standardization.
6. **Automated Crack Detection Engine**: High-confidence crack presence classification using optimized ONNX transfer learning with 8-view rotation/flip Test-Time Augmentation (TTA).

### Milestone 2: Advanced Deep Learning & Defect Intelligence
7. **Pixel-Level Crack Segmentation Engine**: U-Net architecture producing binary segmentation masks, boundary contours, and morphological skeleton extraction.
8. **Crack Type Classification Engine**: Morphology-driven classifier categorizing cracks into 8 distinct engineering classes with orientation angle and branching analysis.
9. **Surface Damage Detection Engine**: Multi-class defect detector identifying 9 infrastructure damage types with localized bounding boxes and individual defect confidence scores.
10. **Crack Geometry & Calibration Engine**: Calculates total crack length ($mm$), maximum aperture width ($mm$), mean width ($mm$), defect area ($mm^2$), surface crack density ($\% = \frac{\text{Defect Area}}{\text{Surface Area}} \times 100$), and branching intersection count.
11. **Damage Severity Assessment Engine**: Multi-factor weighted severity indexing (No Visible Damage, Minor, Moderate, Severe, Critical / Urgent Review) mapping crack width ($>2.0mm$ critical threshold), length, and density.

### Milestone 3: Model Evaluation, Explainability & Geospatial Intelligence
12. **Model Training & Comparison Registry**: Comparative evaluation dashboard benchmarking MobileNetV3-TTA, YOLOv8, SegFormer, ResNet-50, and U-Net across accuracy, precision, recall, F1, inference latency, and parameter footprint.
13. **Model Management & Rollout**: Production model registry enabling zero-downtime hot-swapping between registered models.
14. **Explainable AI (XAI) Visualizer**: Tri-mode explainability suite (Grad-CAM, Grad-CAM++, Input Saliency) revealing convolutional feature activations.
15. **Geospatial Damage Mapping**: Interactive Leaflet GIS map visualizing asset locations, maintenance priority markers, and defect density heatmaps.
16. **Damage Progression & Comparison Engine**: Multi-inspection delta analysis calculating crack length growth, aperture expansion rates, and newly emerged defects with automated trend status (*Stable*, *Active Progression*, *Accelerated Deterioration*, *Repaired*).

### Milestone 4: Operational Workflows, Reporting & Deployment
17. **Maintenance Prioritization Engine**: Automated priority queue ranking assets by composite structural risk score ($0\text{--}100$) derived from defect severity, structural age, and inspection recency.
18. **Work Order Management System**: Full-lifecycle maintenance ticketing (Open, In Progress, Resolved) with priority tiering, cost estimation, due dates, and resolution notes.
19. **Role-Tailored Dashboard Consoles**: Personalized dashboard views tailored for Executives, Field Inspectors, Civil Engineers, Asset Managers, and System Administrators.
20. **Multi-Format Inspection Reporting**: Instant download of official engineering PDF reports (with professional engineer signoff block and legal disclaimer), CSV data exports, openpyxl Excel workbooks, and REST JSON payloads.
21. **Notification & Safety Alert System**: Role-targeted notification bell with unread badges, automated alerts on critical crack emergence ($>2.0mm$), and mark-as-read controls.
22. **Containerization & Deployment**: Dockerized microservices architecture with `backend/Dockerfile`, `frontend/Dockerfile` (Nginx SPA proxy), and `docker-compose.yml` orchestrating PostgreSQL, FastAPI, and React.

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend Framework** | Python 3.11, FastAPI, Pydantic v2, Starlette |
| **Database & ORM** | PostgreSQL 15, SQLite 3 (zero-setup dev), SQLAlchemy 2.0 |
| **Authentication & Security** | OAuth2 Password Bearer, JWT (`python-jose`), `passlib[bcrypt]` |
| **AI / ML & Computer Vision** | ONNX Runtime, PyTorch 2.2, Torchvision, OpenCV (`opencv-python-headless`), Pillow, NumPy, SciPy |
| **Reporting & Data Export** | ReportLab (PDF), openpyxl (Excel), Pandas, Python CSV |
| **Frontend Framework** | React 18, Vite, TypeScript, Tailwind CSS, Lucide Icons |
| **Interactive GIS Maps** | Leaflet, React-Leaflet, OpenStreetMap |
| **Testing & Quality Assurance** | Pytest 8.2, pytest-asyncio, HTTPX TestClient |
| **Containerization & Web Server** | Docker, Docker Compose, Nginx Alpine, Uvicorn |

---

## Quickstart Guide

### Option A: Local Development Setup (Recommended for quick testing)

#### 1. Backend Setup
```powershell
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run server (initializes SQLite infrascan.db and seeds initial roles & admin accounts automatically)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be live at:
- **Interactive Swagger UI**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`

#### 2. Frontend Setup
```powershell
# In a new terminal, navigate to frontend directory
cd frontend

# Install Node modules
npm install

# Start Vite development server
npm run dev
```
Access the application at `http://localhost:5173`.

---

### Option B: Docker Compose Multi-Container Deployment

Run the complete production-configured stack (PostgreSQL + FastAPI + Nginx React Frontend):

```bash
docker compose up -d --build
```

- **Frontend Application**: `http://localhost:80` (or `http://localhost:3000`)
- **Backend API**: `http://localhost:8000`
- **Interactive Docs**: `http://localhost:8000/docs`
- **PostgreSQL Database**: `localhost:5432` (`infrascan_db`)

To stop containers:
```bash
docker compose down
```

---

## Seed Accounts & Role Credentials

When the database initializes, the platform automatically seeds credentials for all 5 roles:

| Role | Email | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@infrascan.ai` | `Admin123!` | Complete system access, user management, audit logs, model registry |
| **Civil Engineer** | `engineer@infrascan.ai` | `Engineer123!` | AI inference analysis, calibration, report export, XAI visualization |
| **Infrastructure Inspector** | `inspector@infrascan.ai` | `Inspector123!` | Asset inspections, live camera capture, field notes upload |
| **Maintenance Engineer** | `maintenance@infrascan.ai` | `Maintenance123!` | Work order execution, resolution logging, maintenance queue |
| **Infrastructure Manager** | `manager@infrascan.ai` | `Manager123!` | Asset inventory, scheduling, budget review, GIS fleet overview |

---

## Automated Test Suite

InfraScan includes an automated test suite verifying auth security, RBAC enforcement, asset CRUD, image validation pipelines, AI inference, Grad-CAM generation, crack segmentation, work orders, notifications, multi-format reports, and model versioning.

Execute tests via:
```powershell
backend\venv\Scripts\python.exe -m pytest backend/tests/ -v
```

```text
============================= test session starts =============================
collected 12 items

backend/tests/test_ai_inference.py::test_inference_pipeline_cracked PASSED [  8%]
backend/tests/test_ai_inference.py::test_inference_pipeline_intact PASSED  [ 16%]
backend/tests/test_ai_inference.py::test_segmentation_and_geometry PASSED  [ 25%]
backend/tests/test_ai_inference.py::test_generate_inspection_pdf PASSED    [ 33%]
backend/tests/test_api_endpoints.py::test_register_and_login PASSED        [ 41%]
backend/tests/test_api_endpoints.py::test_role_denial_admin_endpoint PASSED[ 50%]
backend/tests/test_api_endpoints.py::test_asset_crud PASSED                [ 58%]
backend/tests/test_api_endpoints.py::test_image_validations PASSED         [ 66%]
backend/tests/test_api_endpoints.py::test_work_orders_crud PASSED          [ 75%]
backend/tests/test_api_endpoints.py::test_notifications_endpoints PASSED   [ 83%]
backend/tests/test_api_endpoints.py::test_inspection_reports_and_progression PASSED [ 91%]
backend/tests/test_api_endpoints.py::test_model_versioning_and_metrics PASSED [100%]

======================= 12 passed in 6.55s =======================
```

---

## Key API Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/auth/login` | Authenticate user & issue JWT bearer token |
| `GET` | `/assets/` | List infrastructure assets with search and type filters |
| `POST` | `/inspections/{id}/images` | Upload inspection images with blur/duplicate quality check |
| `POST` | `/images/{id}/analyze` | Execute AI defect detection, segmentation, and geometry extraction |
| `GET` | `/images/{id}/preview?mode={mode}` | Fetch image preview (`original`, `enhanced`, `sharpen`, `shadow_reduction`, `edge`, `texture`, `roi`, `gradcam`, `gradcam_plus`, `saliency`, `mask`, `skeleton`, `boxes`) |
| `PUT` | `/images/{id}/calibration` | Update physical millimeter-per-pixel scale calibration ($mm/px$) |
| `GET` | `/inspections/{id}/compare/{prev_id}` | Compare current inspection against previous inspection of same asset |
| `GET` | `/inspections/asset/{id}/progression` | Retrieve historical time-series defect degradation timeline |
| `GET` | `/inspections/{id}/report/pdf` | Download signed engineering inspection report (PDF) |
| `GET` | `/inspections/{id}/report/excel` | Download itemized inspection report workbook (.xlsx) |
| `GET` | `/inspections/{id}/report/csv` | Download tabular defect data (CSV) |
| `GET` | `/inspections/{id}/report/json` | Retrieve structured inspection assessment payload (JSON) |
| `GET` | `/work-orders/` | List maintenance work orders with priority and status filters |
| `POST` | `/work-orders/` | Create a new maintenance work order |
| `GET` | `/notifications/` | Fetch real-time system and critical safety notifications |
| `GET` | `/analytics/model-comparison` | Benchmark model metrics (accuracy, latency, parameters) |
| `POST` | `/analytics/models/{id}/deploy` | Roll out or hot-swap production AI model |
| `GET` | `/analytics/models/evaluation-metrics` | Retrieve confusion matrix, ROC-AUC, and class performance data |

---

## License & Engineering Standards
InfraScan is developed for civil engineering infrastructure condition monitoring. Thresholds and severity indices are aligned with general structural rehabilitation guidelines (ACI 224.1R, FHWA Bridge Inspector's Reference Manual).
