# InfraScan 🏗️
**AI-powered crack and damage assessment for civil infrastructure.**

> ⚠️ **Decision Support Notice**: AI results are decision support, not a structural safety evaluation. Always consult a licensed professional engineer.

---

## Prerequisites

| Tool | Version | Recommended Download |
|------|---------|----------------------|
| **Python** | 3.11+ | [python.org](https://python.org) |
| **Node.js** | 18+ | [nodejs.org](https://nodejs.org) |
| **Docker Desktop** | Latest | [docker.com](https://docker.com) *(Optional for PostgreSQL)* |

---

## Tech Stack (Milestone 1)

- **Backend**: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.x, JWT (`python-jose`), `passlib[bcrypt]` (pinned `bcrypt==4.0.1`), OpenCV (`opencv-python-headless`), Pillow, NumPy, Pytest.
- **Database**: SQLite fallback (`sqlite:///./infrascan.db`) out-of-the-box or PostgreSQL via Docker Compose (`docker compose up -d`).
- **Storage**: Local filesystem abstraction (`app.services.storage.LocalStorage`) ready to swap to AWS S3 / MinIO in Milestone 2.
- **Frontend**: React 18, Vite, TypeScript, Tailwind CSS, React Router v6, Axios, Lucide Icons.

---

## Quick Start Guide

### 1. Database & Backend Setup

```powershell
# In terminal 1 (PowerShell):
cd backend

# Create & activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r requirements.txt

# Seed roles, demo accounts, and 3 sample civil assets
python seed_data.py

# Launch the FastAPI backend server
uvicorn app.main:app --reload --port 8000
```

- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc API Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

### 2. Frontend Setup

```powershell
# In terminal 2:
cd frontend

# Install dependencies (already prepared)
npm install

# Start Vite React development server
npm run dev
```

- **Frontend Application**: [http://localhost:5173](http://localhost:5173)

---

## Pre-Seeded Test Accounts

All accounts are created with password: `Password123!`

| Role | Email | Permissions |
|------|-------|-------------|
| **Administrator** | `admin@infrascan.com` | Complete access, User management (`/admin/users`), Role assignment |
| **Infrastructure Manager** | `manager@infrascan.com` | Create/edit/delete assets, assign inspectors |
| **Civil Engineer** | `civil@infrascan.com` | View all assets, review inspections & notes |
| **Infrastructure Inspector** | `inspector@infrascan.com` | Create inspections assigned to self, upload inspection images |
| **Maintenance Engineer** | `maintenance@infrascan.com` | Read-only access to assets and inspections |

---

## Pre-Seeded Civil Infrastructure Assets

1. **`BRG-001`** — *Golden Gate Overpass Viaduct* (Bridge, Reinforced Concrete, Built 1988)
2. **`TUN-002`** — *Metropolitan Metro East Transit Tunnel* (Tunnel, Segmental Cast Concrete, Built 2004)
3. **`DAM-003`** — *Pine Valley Reservoir Gravity Dam* (Dam, Mass Concrete, Built 1974)

---

## Testing & Quality Assurance

Run the automated Pytest test suite covering:
- Authentication & JWT issuance
- Role-based denial (`403 Forbidden`)
- Full Asset CRUD lifecycle
- Image validation (rejecting non-images, images < 64x64, exact MD5 duplicate rejection, blur score assessment)

```powershell
cd backend
.\venv\Scripts\pytest.exe tests/ -v
```

---

## Milestone 1 Complete vs. Milestone 2 Roadmap

### ✅ What is Done (Milestone 1)
- [x] Full Project Structure & Local File Storage Abstraction
- [x] SQLAlchemy 2.0 DB Models (`roles`, `users`, `infrastructure_assets`, `inspections`, `inspection_images`, `audit_logs`)
- [x] JWT Authentication & strict Role-Based Access Control (`Administrator`, `Infrastructure Manager`, `Civil Engineer`, `Infrastructure Inspector`, `Maintenance Engineer`)
- [x] Audit Logging service on login, register, create, update, delete
- [x] Google OAuth2 endpoint stub (`501 Not Implemented`)
- [x] Infrastructure Assets API (CRUD, pagination, text search, type filter, coordinate validation)
- [x] Inspection Management API (create, assign inspector, list by asset, status transitions)
- [x] Image Upload Pipeline (multipart, resolution >= 64x64, size <= 20MB, duplicate MD5 check, safe UUID filename)
- [x] Image Quality & Preprocessing (Laplacian blur score, brightness score, CLAHE contrast enhancement, 224x224 resize, ImageNet normalization tensor)
- [x] Full React + Vite + TypeScript frontend with Tailwind UI, Sidebar, AuthContext, Protected Routes, and original vs. CLAHE comparison modal
- [x] Comprehensive Pytest test suite

### 🔮 What is Next (Milestone 2)
- **AI Inference Engine**: YOLOv8 crack and spalling detection, U-Net semantic segmentation for concrete defect area quantification
- **Interactive GIS Map**: PostGIS geometry + Leaflet map view of assets
- **PDF Report Generation**: Automated structural inspection reports with damage severity indices
- **Cloud Object Storage**: S3 / MinIO backend adapter for `LocalStorage`
- **Real-Time Notifications & WebSockets**: Alerts on severe damage detection

---

## Dataset research and EDA

Dataset comparison, licenses, and download status:

- [`docs/InfraScan_Dataset_Research.xlsx`](docs/InfraScan_Dataset_Research.xlsx)
- [`docs/InfraScan_EDA_Report.md`](docs/InfraScan_EDA_Report.md)
- [`datasets/README.md`](datasets/README.md)

```powershell
python -m pip install -r requirements-eda.txt
python scripts/eda_infrascan.py --help
python scripts/eda_infrascan.py --dataset all
```

Do not commit image archives. See `.gitignore` and `datasets/README.md`.
