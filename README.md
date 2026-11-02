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

## Tech Stack

- **Backend**: Python 3.12 for model training and serving (PyTorch has no Python 3.14 wheel), FastAPI, Pydantic v2, SQLAlchemy 2.x, JWT (`python-jose`), `passlib[bcrypt]` (pinned `bcrypt==4.0.1`), OpenCV, Pillow, NumPy, Pytest.
- **Models**: PyTorch SmallCNN, a compact U-Net, and an Ultralytics YOLOv8n fine-tune. CPU is supported. Install with `scripts/setup_ml_env.ps1`.
- **Database**: SQLite fallback (`sqlite:///./infrascan.db`) out-of-the-box or PostgreSQL via Docker Compose (`docker compose up -d`).
- **Storage**: Local filesystem (`app.services.storage.LocalStorage`).
- **Frontend**: React, Vite, TypeScript, Tailwind CSS, React Router, Axios, Lucide Icons.

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

## Milestone status

Milestone 1 (accounts, assets, inspections, upload, quality checks, React UI) is in place and covered by pytest.

Milestone 2 adds CPU baselines and connects them to `POST /images/{id}/analyze`:

- SmallCNN crack / non-crack patches. Validation F1 **0.8267** on 144 DeepCrack patches.
- Compact U-Net. Validation Dice **0.4316**, IoU **0.3449** on 8 images.
- YOLOv8n fine-tune on 60 RDD2022 Czech images. Validation mAP50 **0.0004**. The pipeline runs. The detector is not accurate enough to rely on.

Start both apps with `.\scripts\start_infrascan.ps1`. The click path, sample image, and the sentences to say out loud are in [`docs/DEMO_GUIDE.md`](docs/DEMO_GUIDE.md).

| Document | What it contains |
|---|---|
| [`docs/MILESTONE_1_COMPLETION_REPORT.md`](docs/MILESTONE_1_COMPLETION_REPORT.md) | Dataset facts checked against the EDA files, and which app features were tested |
| [`docs/MILESTONE_2_COMPLETION_REPORT.md`](docs/MILESTONE_2_COMPLETION_REPORT.md) | Training commands and the live analysis output |
| [`docs/MODEL_EVALUATION_REPORT.md`](docs/MODEL_EVALUATION_REPORT.md) | Metrics, confusion matrix, and which baseline to quote |
| [`docs/FINAL_SYSTEM_ARCHITECTURE.md`](docs/FINAL_SYSTEM_ARCHITECTURE.md) | Diagram of the running system |
| [`docs/DEMO_GUIDE.md`](docs/DEMO_GUIDE.md) | Tomorrow's demonstration |
| [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md) | What is still weak, missing, or blocked |

Google sign-in is still HTTP 501. Maps, PDF reports, and cloud storage are not in this build.

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
