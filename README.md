# InfraScan — AI-Powered Crack & Damage Assessment for Civil Infrastructure

Modular full-stack platform for civil infrastructure inspection, crack detection, damage assessment, geospatial mapping, and reporting.

## Repository Structure

```text
InfraScan/
├── backend/         # FastAPI REST API, SQLAlchemy ORM, JWT auth, ML inference engine
├── frontend/        # React + TypeScript + Vite + Tailwind CSS application
├── eda/             # Exploratory data analysis scripts and dataset audit reports
├── ml/              # Dataset preprocessing, annotation cleaning, YOLO training & configs
├── docs/            # Architecture, API, dataset, model docs & Milestone 1-4 reports
├── scripts/         # Convenience startup scripts
└── dataset_audit/   # Original & processed RDD2022 dataset workspace (preserved)
```

## Quick Start

### Backend
```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

### Frontend
```powershell
cd frontend
npm run dev
```

Or use the scripts in `scripts/`:
- `.\scripts\start-backend.ps1`
- `.\scripts\start-frontend.ps1`
