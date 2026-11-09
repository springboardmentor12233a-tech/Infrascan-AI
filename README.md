# InfraScan 🏗️
**AI-Powered Civil Infrastructure Crack & Damage Assessment Platform**

> ⚠️ **Decision Support Notice**: AI results are decision support tools for infrastructure inspection planning and should not replace certified structural engineering evaluations. Always consult a licensed professional engineer.

---

## System Overview

InfraScan is an end-to-end AI platform for physical infrastructure condition assessment. It ingests inspection imagery across bridges, concrete walls, pavements, and industrial facilities, analyzes defect signatures with deep learning, extracts millimeter-level crack geometry, generates visual Grad-CAM explainability maps, and produces downloadable engineering reports.

- **Verified Defect Accuracy**: **94.60%** overall classification accuracy across dual benchmark datasets (SDNET2018 + METU Concrete Benchmark).
- **Inference Latency**: Sub-30ms CPU inference using an optimized ONNX Runtime execution engine.
- **Explainable AI (XAI)**: Gradient-weighted Class Activation Mapping (Grad-CAM) spatial heatmaps.
- **Geometric Quantification**: Pixel skeletonization, Euclidean distance transform, bounding box defect localization, and crack morphology classification.
- **Inspection Reporting**: Automated ReportLab PDF structural inspection report generation with damage severity indexing.
- **Geospatial Mapping**: Interactive Leaflet & OpenStreetMap GIS visualization for infrastructure assets and defect distributions.

---

## Tech Stack

- **Backend**: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.x, JWT (`python-jose`), `passlib[bcrypt]`, PyTorch, Torchvision, ONNX Runtime, OpenCV, Pillow, ReportLab, NumPy, Pytest.
- **Database**: SQLite default (`sqlite:///./infrascan.db`) with out-of-the-box zero-setup or PostgreSQL via Docker Compose.
- **Storage**: Pluggable storage abstraction (`LocalStorage`) for image uploads, thumbnails, and preview artifacts.
- **Frontend**: React 18, Vite, TypeScript, Tailwind CSS, React Router v6, Axios, Leaflet, Lucide Icons.

---

## Repository Structure

```text
infra-scan/
├── backend/
│   ├── app/
│   │   ├── models/           # SQLAlchemy DB models (User, Role, Asset, Inspection, Image)
│   │   ├── routers/          # FastAPI routers (auth, users, assets, inspections, images)
│   │   ├── schemas/          # Pydantic v2 input/output schemas
│   │   ├── services/         # Business logic (inference, segmentation, reporting, preprocessing)
│   │   └── database.py       # Engine and session configuration
│   ├── ml/
│   │   ├── models/           # crack_classifier.onnx & crack_classifier.pt
│   │   ├── download_metu_dataset.py  # Automated METU benchmark dataset downloader
│   │   ├── train_model.py    # Dual-dataset training pipeline
│   │   ├── evaluate_model.py # Formal model & geometry evaluation script
│   │   └── export_onnx.py    # ONNX export and validation utility
│   ├── tests/
│   │   ├── test_ai_inference.py   # AI inference, Grad-CAM & segmentation unit tests
│   │   └── test_api_endpoints.py  # Auth, RBAC, asset CRUD & image upload tests
│   ├── requirements.txt
│   └── uploads/              # Local storage repository for inspection imagery
├── frontend/
│   ├── src/
│   │   ├── components/       # AssetMap, Layout, Navbar, Footer
│   │   ├── pages/            # LandingPage, Dashboard, AssetList, AssetDetail, InspectionView
│   │   ├── context/          # AuthContext (JWT session management)
│   │   └── api/              # Axios client with bearer token interceptors
│   ├── package.json
│   └── vite.config.ts
├── outputs/
│   └── eda/                  # Exploratory data analysis & model_evaluation_report.json
├── docker-compose.yml        # PostgreSQL service definition
└── README.md
```

---

## Quick Start Guide

### 1. Backend Setup

```powershell
cd backend

# Create & activate Python virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install -r requirements.txt

# Start development server on http://localhost:8000
python -m uvicorn app.main:app --port 8000 --host 0.0.0.0 --reload
```

Interactive API documentation will be available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### 2. Frontend Setup

```powershell
cd frontend

# Install Node modules
npm install

# Start Vite dev server on http://localhost:5173
npm run dev
```

---

## Machine Learning Pipeline

### Dual-Dataset Training & Evaluation
To prevent single-domain overfitting, the classifier is trained on an 8,000-image composite pool combining **SDNET2018** (civil infrastructure: bridges, walls, pavements) and the **METU Concrete Benchmark** (concrete surfaces).

```powershell
# 1. Download secondary benchmark dataset (METU)
python backend/ml/download_metu_dataset.py

# 2. Train MobileNetV3-Small on composite dataset
python backend/ml/train_model.py

# 3. Export weights to ONNX format
python backend/ml/export_onnx.py

# 4. Run formal evaluation suite
python backend/ml/evaluate_model.py
```

### Verified Benchmark Performance

| Metric | Measured Value |
| :--- | :---: |
| **Overall Classification Accuracy** | **94.60%** |
| **Precision** | **95.14%** |
| **Recall** | **94.00%** |
| **F1-Score** | **94.57%** |
| **Concrete Surface Benchmark** | **100.00%** |
| **Concrete Wall Benchmark** | **95.00%** |
| **Pavement & Deck Benchmark** | **89.00%** |
| **Segmentation Dice Similarity** | **1.0000** |

---

## Running the Automated Test Suite

```powershell
cd backend
python -m pytest tests/ -v
```

All 8 core test suites will execute across API endpoints and the AI inference engine.

---

## Seed Accounts

When initializing the database, the following role-based accounts are pre-seeded:

| Role | Email | Password |
| :--- | :--- | :--- |
| **Administrator** | `admin@infrascan.ai` | `Admin123!` |
| **Civil Engineer** | `engineer@infrascan.ai` | `Engineer123!` |
| **Infrastructure Inspector** | `inspector@infrascan.ai` | `Inspector123!` |
| **Maintenance Engineer** | `maintenance@infrascan.ai` | `Maintenance123!` |
| **Infrastructure Manager** | `manager@infrascan.ai` | `Manager123!` |
