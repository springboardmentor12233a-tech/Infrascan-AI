# InfraScan Quickstart & Operations Guide (`user_quickstart.md`)

> **Security & Honesty Note**: Demo user credentials are generated dynamically into the local, gitignored file `docs/final/demo_accounts.local.txt`. Never commit credentials to version control. All AI detections and severity scores carry the disclaimer: *"AI result for engineer review, not a final structural safety verdict."*

---

## 1. Prerequisites

- **Operating System**: Windows 10/11 x64
- **Python**: 3.10+ (tested on Python 3.12.10) with venv at `infrascan/backend/venv`
- **Node.js**: v18+ (tested on Node v22.20.0) with dependencies installed in `infrascan/frontend`
- **Database**: PostgreSQL 17 on `localhost:5432` with database `infrascan_db` (or SQLite fallback for tests)
- **Model Weights**:
  - `ml/detection/yolov8s_rdd2022/weights/best.pt` (Road damage detector)
  - `ml/models/segmentation/unetplusplus_crack500/best.pth` (Crack segmentation)
  - `ml/models/detection_codebrim/A2_rtdetr_l/weights/best.pt` (Defect transformer)

---

## 2. One-Command Operations

### 2.1 Starting the Complete Environment
Run the orchestration PowerShell script from the repository root:
```powershell
.\scripts\run_dev.ps1
```
This script automatically:
1. Validates Python runtime, virtual environment, and Node.js.
2. Runs `scripts/doctor.py` checking database connection, packages, weights SHA-256 hashes, and smoke inference.
3. Applies database schema migrations and initial indexes.
4. Starts the **FastAPI Backend** (`127.0.0.1:8000`) in its own terminal.
5. Starts the **AI Job Worker** (`app/worker.py` with `SKIP LOCKED` and heartbeats) in its own terminal.
6. Starts the **Vite Frontend** (`127.0.0.1:5173`) in its own terminal.
7. Polls `http://127.0.0.1:8000/readyz` until healthy, then automatically launches your default browser.

### 2.2 Stopping All Services
```powershell
.\scripts\stop_dev.ps1
```
Gracefully terminates backend (port 8000), frontend (port 5173), and background Python worker processes.

### 2.3 Resetting the Demo Environment
```powershell
.\scripts\reset_demo.ps1
```
1. Purges demo records from the database using `demo_markers`.
2. Seeds fresh demo users for all 5 roles and writes random passwords to `docs/final/demo_accounts.local.txt`.
3. Seeds 12 demo infrastructure assets and inspection records around Chennai, Kanchipuram, and Thanjavur.

---

## 3. Demo User Accounts

Credentials are generated dynamically by `scripts/seed_demo_users.py` into `docs/final/demo_accounts.local.txt`:

| Role | Email Identifier | Default Permissions |
|---|---|---|
| **System Admin** | `demo_admin@demo.infrascan.local` | Full user administration, jobs, audit logs, models |
| **Operations Manager** | `demo_manager@demo.infrascan.local` | Asset creation, inspection scheduling, portfolio map |
| **Civil Engineer** | `demo_civil@demo.infrascan.local` | Severity certification, priority confirmation, reports, tasks |
| **Field Inspector** | `demo_inspector@demo.infrascan.local` | Photo capture, upload queue, scale calibration |
| **Maintenance Engineer** | `demo_maint@demo.infrascan.local` | Work order execution, repair notes, status updates |

---

## 4. Key Application Endpoints

- **Frontend User Interface**: [http://127.0.0.1:5173](http://127.0.0.1:5173)
- **Backend API Base**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive OpenAPI Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Liveness Probe**: [http://127.0.0.1:8000/healthz](http://127.0.0.1:8000/healthz)
- **Readiness & Worker Status Probe**: [http://127.0.0.1:8000/readyz](http://127.0.0.1:8000/readyz)
- **Prometheus Metrics Stream**: [http://127.0.0.1:8000/metrics](http://127.0.0.1:8000/metrics)
