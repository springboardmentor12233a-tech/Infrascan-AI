# InfraScan – AI-Powered Crack & Damage Assessment for Civil Infrastructure

InfraScan is an end-to-end, AI-powered infrastructure crack and damage assessment platform. It combines a production-ready **FastAPI** backend and **React + TypeScript + Vite + Tailwind CSS** frontend with a deep learning Computer Vision suite for automated defect classification, object detection, pixel-level semantic segmentation, and sub-pixel geometric crack quantification.

---

## Project Overview & Objectives

Civil infrastructure inspection requires accurate, automated, and repeatable defect identification to prioritize maintenance and prevent catastrophic failures. InfraScan addresses this through:

- **Full-Stack Asset & Inspection Management**: Role-based access control (RBAC), asset mapping, inspection scheduling, image uploads, and immutable audit logging.
- **Exploratory Data Analysis (EDA) & Data Cleaning**: Multi-dataset quality auditing, perceptual hash near-duplicate removal, and leakage-free dataset splitting.
- **Deep Learning Vision Suite**:
  - Binary crack classification (ResNet-50).
  - Multi-class road damage distress detection (YOLOv8s / YOLO11s).
  - High-resolution semantic crack segmentation (U-Net and U-Net++ with ResNet-34 backbones).
- **Sub-Pixel Geometric Quantification**: Medial axis skeletonization and Euclidean Distance Transform (EDT) algorithms to calculate crack length, average/maximum width, orientation, and tortuosity.

---

## Project Structure

```text
infrascan/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point, lifespan DB init, CORS, routers
│   │   ├── config.py                # Pydantic settings from backend/.env (DB, JWT secrets)
│   │   ├── database.py              # SQLAlchemy engine, SessionLocal, Base model
│   │   ├── deps.py                  # Authentication dependencies & role verification
│   │   ├── models/                  # SQLAlchemy ORM: users, assets, inspections, audit_logs
│   │   ├── schemas/                 # Pydantic request/response validation schemas
│   │   ├── services/                # Security (bcrypt, PyJWT) and audit logging services
│   │   ├── routers/                 # API routes: /auth, /users, /assets, /inspections
│   │   └── ai/                      # Computer vision inference modules & quality checks
│   ├── scripts/
│   │   ├── seed_admin.py            # CLI script to seed administrator accounts
│   │   └── seed_assets.py           # CLI script to seed Chennai infrastructure assets
│   ├── tests/
│   │   ├── test_auth.py             # Automated tests for authentication & RBAC
│   │   └── test_assets_inspections.py # Automated tests for assets & inspection workflows
│   ├── .env.example                 # Template environment variables
│   └── requirements.txt             # Python backend dependencies
├── frontend/
│   ├── src/
│   │   ├── api/                     # Axios client with JWT interceptor & typed endpoints
│   │   ├── context/                 # AuthContext (JWT session state, login, logout)
│   │   ├── components/              # Reusable UI: Navbar, ProtectedRoute, StatusBadge
│   │   ├── pages/                   # Login, Register, Dashboard, Profile, Users, Assets, Inspections
│   │   ├── App.tsx                  # React Router application routing
│   │   ├── main.tsx                 # React DOM mount point
│   │   └── index.css                # Tailwind CSS stylesheets
│   ├── package.json                 # Frontend dependencies & build scripts
│   ├── vite.config.ts               # Vite build configuration
│   └── tsconfig.json                # TypeScript project configuration
├── ml/
│   ├── classification/              # ResNet-50 crack classification training & evaluation
│   │   ├── config.py                # Hyperparameters, augmentations, and seeds
│   │   ├── train_classifier.py      # ResNet-50 training script with early stopping
│   │   └── evaluate_classifier.py   # Comprehensive test evaluation & metrics export
│   ├── detection/                   # Road distress object detection (RDD2022)
│   │   ├── config.py                # YOLOv8s / YOLO11s hyperparameters and classes
│   │   ├── train_yolo.py            # Ultralytics training wrapper
│   │   └── evaluate_yolo.py         # Multi-class validation & evaluation script
│   ├── segmentation/                # U-Net & U-Net++ semantic segmentation
│   │   ├── evaluate_seg_test.py     # Crack500 test & CFD benchmark evaluation
│   │   └── run_remaining_steps.py   # Leakage audit, speed benchmark, and summary generator
│   ├── geometry/                    # Crack skeletonization & width calculation
│   │   ├── crack_geometry.py        # measure_crack function (length, width, skeleton)
│   │   ├── validate_geometry.py     # Synthetic shape validation suite (0°-75° angles, arcs)
│   │   └── run_geometry.py          # Batch evaluation on Crack500 masks & overlay generator
│   └── data_prep.py                 # Multi-dataset cleaning, deduplication, and VOC/YOLO converter
├── notebooks/                       # Complete project Jupyter notebooks
│   ├── 01_dataset_structure.ipynb   # Raw dataset structure & annotation auditing
│   ├── 02_eda.ipynb                 # Exploratory data analysis, pixel stats & dimensions
│   ├── 03_class_distribution.ipynb  # Class balance & distress type analysis
│   ├── 03_preprocessing_demo.ipynb  # Milestone 1 image preprocessing & enhancement demo
│   ├── 04_dataset_cleaning.ipynb    # Perceptual hash deduplication & split generation
│   ├── 05_train_resnet50_colab.ipynb# Classification training on Google Colab
│   ├── 06_evaluate_classifiers_colab.ipynb # Classifier test evaluation
│   ├── 07_train_yolo_colab.ipynb    # YOLO training on Colab
│   ├── 07_train_yolo_kaggle.ipynb   # YOLO training on Kaggle GPU
│   ├── 08_evaluate_yolo_colab.ipynb # YOLO evaluation on Colab
│   ├── 08_evaluate_yolo_kaggle.ipynb# YOLO evaluation on Kaggle
│   ├── 09_train_seg_kaggle.ipynb    # U-Net & U-Net++ training on Kaggle
│   ├── 10_eval_seg_kaggle.ipynb     # Segmentation validation threshold sweep
│   └── 11_evaluate_seg_test.ipynb   # Test evaluation & zero-shot generalization
└── docs/                            # Documentation, evaluation reports, and figures
    ├── 08_dataset_cleaning.md       # Data cleaning & partitioning specification
    ├── 10_crack_geometry.md         # Crack geometry methodology & validation report
    ├── 11_milestone2_results.md     # Milestone 2 experimental results summary
    ├── 12_model_evaluation_report.md# Formal Milestone 2 Model Evaluation Report
    ├── 12_model_evaluation_report.pdf# Formatted evaluation report document
    ├── 12_number_sources.csv        # Complete metric traceability audit appendix
    └── figures/                     # 24 evaluation figures (ROC, PR, confusion matrices, overlays)
```

---

## Current Status

- **Milestone 1**: Completed. Full-stack infrastructure management platform, authentication, role-based workflows, SQLite/PostgreSQL database, image preprocessing pipelines, and automated test suite.
- **Milestone 2**: Completed. Multi-dataset EDA, ResNet-50 crack classifiers, YOLO road distress detectors, U-Net++ crack segmentation with test and zero-shot CFD evaluation, sub-pixel crack geometry quantification, and formal model evaluation report.

---

## Milestone 1 Implementation: Web Application & Platform Architecture

### Authentication & Role-Based Access Control (RBAC)

The platform enforces strict role-based access control across 5 distinct organizational roles:

| Role | Permissions & Access Scope |
|---|---|
| `inspector` | Views assigned inspections, marks inspections `in_progress` or `completed`, views infrastructure assets. |
| `civil_engineer` | Schedules inspections, views all inspections across assets, updates inspection status, reviews assets. |
| `maintenance_engineer` | Views infrastructure assets, reviews inspection records, tracks defect repair histories. |
| `manager` | Creates and updates infrastructure assets, schedules inspections, manages engineering workflows. |
| `admin` | Full system governance: user provisioning, role assignments, account activation/deactivation, asset management, and inspection auditing. |

#### Security Implementation
- **Password Hashing**: Direct `bcrypt` hashing with salt rounds (minimum 8 characters enforced).
- **JWT Authentication**: Signed access tokens via `PyJWT` with configurable expiration (default 30 minutes).
- **Immutable Audit Logging**: Security-critical actions (`register`, `login_success`, `login_failure`, `password_change`, `role_change`, `account_activated`, `create_asset`, `update_asset`, `delete_asset`, `create_inspection`, `update_inspection_status`) are logged to the `audit_logs` table with timestamps and actor IDs.

---

### Database Seeding Scripts

#### 1. Seed Administrator User
```powershell
cd "backend"
python scripts/seed_admin.py --email admin@infrascan.com --password Admin12345 --name "System Administrator"
```

#### 2. Seed Chennai Infrastructure Assets
Populates sample bridge, road, tunnel, building, and dam assets in Chennai, Tamil Nadu (Bridge B-12, Road NH-48, Tunnel T-3, Building A, Dam D-1, Wall W-7):
```powershell
cd "backend"
python scripts/seed_assets.py
```

---

### How to Run the Application

#### 1. Backend Server (Terminal 1)
```powershell
cd "backend"
uvicorn app.main:app --reload --port 8000
```
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

#### 2. Frontend Client (Terminal 2)
```powershell
cd "frontend"
npm install
npm run dev
```
- **Web Interface**: [http://localhost:5173](http://localhost:5173)

---

### API Endpoints Summary

#### Authentication & Users
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/health` | Public | Health check returning `{"status": "ok"}` |
| `POST` | `/auth/register` | Public | Register new user (auto-assigned role `inspector`) |
| `POST` | `/auth/login` | Public | OAuth2 password form returning JWT token and role |
| `GET` | `/users/me` | Authenticated | Retrieve current user profile |
| `PUT` | `/users/me` | Authenticated | Update current user profile details |
| `POST` | `/users/me/change-password` | Authenticated | Change user password (requires old password verification) |
| `GET` | `/users/inspectors` | Admin, Manager, Civil Eng | List active users with the `inspector` role |
| `GET` | `/users` | Admin only | List all registered users |
| `PUT` | `/users/{id}/role` | Admin only | Update user role |
| `PUT` | `/users/{id}/active` | Admin only | Activate or deactivate user account |

#### Infrastructure Assets
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/assets` | Admin, Manager | Create a new infrastructure asset |
| `GET` | `/assets` | Authenticated | Paginated asset list with search and type/material filters |
| `GET` | `/assets/geojson` | Authenticated | GeoJSON FeatureCollection with `[lon, lat]` coordinates |
| `GET` | `/assets/{id}` | Authenticated | Detailed asset view with linked inspection history |
| `PUT` | `/assets/{id}` | Admin, Manager | Update existing asset specifications |
| `DELETE` | `/assets/{id}` | Admin only | Delete asset (refused with 400 if active inspections exist) |

#### Inspections & Workflows
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/inspections` | Admin, Manager, Civil Eng | Schedule an inspection (assignee must be an active inspector) |
| `GET` | `/inspections` | Authenticated | List inspections (inspectors see assigned; others see all) |
| `GET` | `/inspections/{id}` | Authenticated | Detailed inspection view with inspection notes |
| `PUT` | `/inspections/{id}/status` | Authenticated | Update status (inspector: `in_progress`/`completed`; Admin/CE: any) |

---

### Automated Test Suite

The backend includes automated pytest coverage for authentication, RBAC, and data workflows:

```powershell
cd "backend"
pytest
```
- `tests/test_auth.py`: 5 tests covering user registration, JWT logins, role enforcement, and password changes.
- `tests/test_assets_inspections.py`: 6 tests covering asset creation, pagination, GeoJSON feeds, and inspection status transitions.

---

## Milestone 2 Implementation: Deep Learning & Computer Vision Suite

### 1. Dataset Research & Exploratory Data Analysis (EDA)

Comprehensive data cleaning and analysis across concrete, asphalt, and masonry crack datasets:
- **Corrupted Image Elimination**: 1 truncated image in SDNET2018 (`7038-23.jpg`) excluded.
- **Perceptual Hash Deduplication**: Exact and near-duplicate removal using Difference Hash (dHash) with Hamming distance threshold $\le 2$. Removed 10 duplicates in Concrete Crack and 50 duplicate pairs in SDNET2018.
- **Leakage Prevention**: Group-aware splitting on SDNET2018 (keeping all crops from the same structural photo in the same split) and tile-aware split auditing on CRACK500 (100% boundary isolation across train, validation, and test partitions).
- **Notebooks**: `notebooks/01_dataset_structure.ipynb`, `notebooks/02_eda.ipynb`, `notebooks/03_class_distribution.ipynb`, `notebooks/04_dataset_cleaning.ipynb`.
- **Documentation**: [`docs/08_dataset_cleaning.md`](docs/08_dataset_cleaning.md).

---

### 2. Crack Classification (ResNet-50)

Transfer learning with ImageNet-pretrained ResNet-50 architectures:
- **Datasets**: Concrete Crack Images for Classification (40,000 images) and SDNET2018 (56,092 images).
- **Pipelines**: `ml/classification/train_classifier.py`, `ml/classification/evaluate_classifier.py`, `ml/classification/config.py`.
- **Results**:
  - `concrete_crack_cls`: Test Macro F1 = **0.9997** (Crack F1: 0.9997, Uncracked F1: 0.9996). Plan target $\ge 0.85$ **Reached**.
  - `sdnet2018`: Test Macro F1 = **0.6421** (Crack F1: 0.4815, Uncracked F1: 0.8027). Target not reached due to complex real-world bridge deck textures, aggregate voids, and casting seams.
- **Notebooks**: `notebooks/05_train_resnet50_colab.ipynb`, `notebooks/06_evaluate_classifiers_colab.ipynb`.

---

### 3. Road Distress Object Detection (YOLOv8s & YOLO11s)

Object detection for localized road distress bounding boxes across 4 categories (`D00` Longitudinal Crack, `D10` Transverse Crack, `D20` Alligator Crack, `D40` Pothole) on RDD2022:
- **Model Selection**: Evaluated on validation split. YOLOv8s achieved **0.2220** mAP@50:95 (mAP@50: 0.4285, Recall: 0.4437), outperforming YOLO11s (**0.2159** mAP@50:95). YOLOv8s chosen as the final detector.
- **Pipelines**: `ml/detection/train_yolo.py`, `ml/detection/evaluate_yolo.py`, `ml/detection/config.py`.
- **Notebooks**: `notebooks/07_train_yolo_colab.ipynb`, `notebooks/07_train_yolo_kaggle.ipynb`, `notebooks/08_evaluate_yolo_colab.ipynb`, `notebooks/08_evaluate_yolo_kaggle.ipynb`.

---

### 4. Semantic Crack Segmentation (U-Net & U-Net++ ResNet-34)

Pixel-level crack segmentation models trained on CRACK500 (384×640 crops) using combined BCE + Dice loss:
- **Model Selection on Validation**: U-Net++ ResNet-34 (Validation Dice **0.7482** at optimal threshold 0.40) selected over standard U-Net (Validation Dice 0.7335 at threshold 0.25).
- **CRACK500 Test Split Evaluation (1,087 images)**:
  - Mean Dice: **0.6899** [95% CI: 0.6801, 0.7001]
  - Mean IoU: **0.5481** [95% CI: 0.5382, 0.5586]
  - Mean Precision: **0.7233** [95% CI: 0.7126, 0.7339]
  - Mean Recall: **0.7188** [95% CI: 0.7077, 0.7299]
  - Zero-crack predictions: 17 images (1.56%) produced empty masks after min-area filtering.
- **Zero-Shot Generalization on CFD Benchmark (118 images)**:
  - Mean Dice: **0.4533** [95% CI: 0.4187, 0.4873]
  - Mean IoU: **0.3109** [95% CI: 0.2839, 0.3384]
  - Analysis: CFD ground-truth crack widths average 4.38 px vs 18.96 px for CRACK500. When comparing width-matched bands (3.89–10.0 px), the performance gap narrows significantly (CRACK500 Dice 0.6163 vs CFD Dice 0.5654).
- **Inference Speed Benchmark**: Host CPU latency is **1,349 ms / image** (under the 3.0s target threshold).
- **Notebooks**: `notebooks/09_train_seg_kaggle.ipynb`, `notebooks/10_eval_seg_kaggle.ipynb`, `notebooks/11_evaluate_seg_test.ipynb`.

---

### 5. Quantitative Crack Geometry Measurement

Sub-pixel geometric characterization module [`ml/geometry/crack_geometry.py`](ml/geometry/crack_geometry.py):
- **Core Algorithms**:
  - Connected component area thresholding (default `min_area = 20 px`).
  - Medial axis skeletonization via `skimage.morphology.skeletonize`.
  - Graph-based step length accumulator weighting orthogonal steps as $1.0$ and diagonal steps as $\sqrt{2}$.
  - Perpendicular crack width estimation using Euclidean Distance Transform ($W = 2 \times \text{EDT}$).
  - Crack orientation angle (degrees) and tortuosity index ($\tau = L / D_{\text{endpoints}}$).
- **Rigorous Synthetic Validation** ([`ml/geometry/validate_geometry.py`](ml/geometry/validate_geometry.py)):
  - Validated on straight lines (widths 2–9 px), rotated polygons (0°, 15°, 30°, 45°, 60°, 75°), and concentric arcs generated at 8× super-resolution.
  - Confirmed deterministic method uncertainty bounded within **$\pm 1.0\text{ px}$**.
- **Full Test Set Geometry Results (CRACK500, 1,087 images)**:
  - Length MAE: **140.32 px** (Mean Signed Error: -39.06 px).
  - Width MAE: **4.74 px** (Mean Signed Error: +0.80 px).
  - Non-empty predictions (1,070 images): Length MAE: 138.04 px, Width MAE: 4.54 px.
- **Documentation**: [`docs/10_crack_geometry.md`](docs/10_crack_geometry.md).

---

### 6. Formal Evaluation Reports & Figures

- **Milestone 2 Evaluation Report**: [`docs/12_model_evaluation_report.md`](docs/12_model_evaluation_report.md) and [`docs/12_model_evaluation_report.pdf`](docs/12_model_evaluation_report.pdf).
- **Metric Traceability Appendix**: [`docs/12_number_sources.csv`](docs/12_number_sources.csv) with exact file provenance for every quoted metric.
- **Milestone 2 Results Summary**: [`docs/11_milestone2_results.md`](docs/11_milestone2_results.md).
- **Visual Diagnostics**: 24 figures under [`docs/figures/`](docs/figures/) including ROC curves, precision-recall curves, confusion matrices, prediction panels (best, median, worst), and skeletonization overlays.

---

## Environment & Security Policy

- Keep all `.env` files and API credentials strictly local.
- Never commit private keys, secrets, virtual environment directories (`venv/`), dependencies (`node_modules/`), caches (`__pycache__/`, `.pytest_cache/`), or large model weight files (`*.pth`, `*.pt`).
- Use `backend/.env.example` as the configuration baseline for local setups.
