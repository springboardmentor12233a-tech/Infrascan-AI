# Milestone 4.4: Dockerization & Deployment Readiness Guide

**Document Date**: November 22, 2026  
**Platform**: InfraScan Civil Infrastructure Damage Inspection Platform  
**System Location**: `E:\infosys\Internship\InfraScan`  

---

## 1. Scope & Objective

Milestone 4.4 delivers production-ready containerization for the InfraScan platform. This documentation specifies:
1. Container architecture (multi-container FastAPI backend + Nginx React SPA).
2. Dockerfiles and multi-stage build optimization.
3. `docker-compose.yml` service orchestration, networking, and health checks.
4. Persistent volume strategies for SQLite database, image uploads, and inspection reports.
5. Environment variable security and secrets management.
6. Execution guidelines and local verification findings.

---

## 2. Docker Architecture Overview

```
                                    [ Browser Client ]
                                            |
                                      Port 80 (HTTP)
                                            v
+-----------------------------------------------------------------------------------------+
|                                  INFRASCAN DOCKER NETWORK                               |
|                                                                                         |
|  +--------------------------------+               +----------------------------------+  |
|  |     infrascan-frontend         |  /api/ &      |       infrascan-backend          |  |
|  |   (Nginx Alpine Web Server)    | ------------> |    (FastAPI + Python 3.11)       |  |
|  |  Serves React Production Build |  /static/     |   Runs AI Services & Business    |  |
|  +--------------------------------+               +----------------------------------+  |
|                                                                    |                    |
+--------------------------------------------------------------------|--------------------+
                                                                     v
                                                   +------------------------------------+
                                                   |      PERSISTENT DOCKER VOLUME      |
                                                   |         (infrascan_data)           |
                                                   |   • infrascan.db (SQLite 3)        |
                                                   |   • /uploads/ (Original Photos)    |
                                                   |   • /results/ (Overlays, Masks)    |
                                                   |   • /reports/ (PDF & CSV Exports)  |
                                                   +------------------------------------+
                                                                     |
                                                   +------------------------------------+
                                                   |       READ-ONLY HOST BIND MOUNT    |
                                                   |            (./models)              |
                                                   |   • yolo_best.pt Checkpoint        |
                                                   +------------------------------------+
```

---

## 3. Container Configurations

### 3.1 Backend Container (`backend/Dockerfile`)
* **Base Image**: `python:3.11-slim`
* **System Libraries**: Installs `libgl1`, `libglib2.0-0`, `libsm6`, `libxext6`, `libxrender-dev`, `libgomp1`, and `curl` for OpenCV headless operations and PyTorch computation.
* **Security & Optimization**:
  * Runs with `--no-cache-dir` on pip installations.
  * Python bytecode generation disabled (`PYTHONDONTWRITEBYTECODE=1`).
  * Unbuffered I/O for real-time logging (`PYTHONUNBUFFERED=1`).
* **Production Command**: Launches with 2 Uvicorn workers without debug reload:
  ```dockerfile
  CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
  ```
* **Health Check**: Automated periodic probe to `http://localhost:8000/api/health`.

### 3.2 Frontend Container (`frontend/Dockerfile` & `frontend/nginx.conf`)
* **Multi-Stage Build**:
  * *Stage 1 (Builder)*: Uses `node:20-alpine`, runs `npm ci`, and compiles the production bundle into `/app/dist`.
  * *Stage 2 (Server)*: Uses `nginx:alpine`, copies compiled assets into `/usr/share/nginx/html`, and configures custom reverse-proxy routing.
* **Nginx Reverse Proxy**:
  * Routes `/api/*` requests directly to `http://backend:8000/api/*` internally.
  * Routes `/static/*` image requests to `http://backend:8000/static/*` internally.
  * Single Page Application fallback: `try_files $uri $uri/ /index.html;` ensures React Router functions correctly.
  * **Zero Hardcoding**: Browser communicates with port 80; the internal Docker network coordinates backend API requests, avoiding `localhost` mismatch issues.

---

## 4. Persistent Storage Strategy

To guarantee zero data loss during container recreation:
* **Docker Named Volume (`infrascan_data`)**:
  * Bound to `/app/data` inside the backend container.
  * Persists `infrascan.db` (all user accounts, inspections, results, and assets).
  * Persists `/app/data/uploads` (raw photographs).
  * Persists `/app/data/results` (generated segmentation masks and Grad-CAM overlays).
  * Persists `/app/data/reports` (generated CSV and PDF files).
* **Model Checkpoint Mount**:
  * Bound from host `./models` to `/app/models:ro` as a **read-only** volume.
  * Ensures large weight files (`yolo_best.pt`, 18.4 MB) are not duplicated into Docker image layers.

> [!CAUTION]
> **CRITICAL DATA PERMANENCE WARNING: `docker compose down -v`**  
> Running `docker compose down -v` (or `--volumes`) will **PERMANENTLY DELETE** the `infrascan_data` volume. This wipes the SQLite database (`infrascan.db`), all uploaded field inspection photos, all generated masks and overlays, and all exported PDF/CSV reports. **Never run `docker compose down -v` in production** unless you have created an independent offline backup. Standard maintenance must use `docker compose down` (without the `-v` flag) to preserve volumes.

---

## 5. Environment Variables & Secret Hardening

Configuration template provided in `.env.example`:
```env
INFRASCAN_ENV=production
INFRASCAN_JWT_SECRET=CHANGEME_GENERATE_A_SECURE_RANDOM_SECRET_KEY
INFRASCAN_STORAGE_DIR=/app/data
INFRASCAN_DB_PATH=/app/data/infrascan.db
INFRASCAN_UPLOAD_DIR=/app/data/uploads
INFRASCAN_RESULTS_DIR=/app/data/results
INFRASCAN_REPORTS_DIR=/app/data/reports
INFRASCAN_MODELS_DIR=/app/models
```
* **Production Guard**: `backend/auth.py` strictly enforces that when `INFRASCAN_ENV=production`:
  1. `INFRASCAN_JWT_SECRET` must be set and non-empty.
  2. The secret must be at least 32 characters in length.
  3. The secret cannot match any known placeholder (e.g. `CHANGEME...`, `replace_with...`). If any violation occurs, a `RuntimeError` terminates backend startup immediately with instructions on generating a secure key.
* **Separation of Development**: In development mode (`INFRASCAN_ENV=development`), a default dev secret is provided automatically so local workflows are unblocked.
* **Exclusion**: `.dockerignore` and `.gitignore` strictly exclude `.env`, `.env.*`, `admin_credentials.txt`, SQLite databases, and private runtime data from image contexts.

---

## 6. Production Configuration Review & Technical Audit

An in-depth architectural audit of the containerization setup reveals the following key assessments:

1. **Persistent Storage**:
   * The `infrascan_data` named volume correctly maps to `/app/data` where the SQLite database, uploaded images, segmentation masks, Grad-CAM overlays, and generated PDF/CSV reports reside.
   * *Assessment*: Data persists across container restarts, stops, and image rebuilds. Volume destruction requires explicit invocation of `docker compose down -v`.
2. **Model Availability & Bind Mounts**:
   * `./models` on the host is bound read-only to `/app/models:ro`, mounting the 18.4 MB `yolo_best.pt` directly into the container.
   * *Physical Check*: Verified that `yolo_best.pt` physically exists at `models/yolo_best.pt` (19,313,732 bytes). It is not assumed available based solely on the mount declaration.
3. **Secret Handling & Zero-Fallback Enforcement**:
   * `docker-compose.yml` uses `${INFRASCAN_JWT_SECRET:?INFRASCAN_JWT_SECRET must be set in .env or environment}` with zero hardcoded fallback string. If `.env` is omitted or lacks the key, Docker Compose halts before launch.
   * `backend/auth.py` halts startup if the configured secret is under 32 characters or matches known placeholder strings.
4. **Nginx API Proxying & Upload Body Size**:
   * `frontend/nginx.conf` proxies `/api/` and `/static/` internally to `http://backend:8000`.
   * *Audit Finding & Correction*: Configured `client_max_body_size 50M;` in `nginx.conf` so high-resolution civil engineering photographs (often 5 MB to 15 MB) are not blocked by Nginx's default 1 MB limit.
5. **Health Checks & Startup Sequencing**:
   * `backend` exposes `curl -f http://localhost:8000/api/health`.
   * `frontend` exposes `wget --spider http://localhost:80/`.
   * In `docker-compose.yml`, `frontend` declares `depends_on: { backend: { condition: service_healthy } }`.
   * *Assessment*: Guarantees the React frontend does not start routing traffic until PyTorch/FastAPI models and database migrations are fully initialized and healthy.
6. **Frontend API URL Configuration**:
   * All frontend client fetches (`AuthContext.jsx`, `InspectionDetail.jsx`, `NewInspection.jsx`) use relative URI paths (e.g. `/api/auth/me`, `/api/inspections`).
   * *Assessment*: No hardcoded `localhost:8000` strings exist in client JavaScript bundles. Requests route naturally to the origin port 80 and are proxied by Nginx to the backend container.

---

## 7. Deployment Commands

### 7.1 Build and Start
```bash
# 1. Create environment file from template
cp .env.example .env

# 2. Generate and set a genuine cryptographically secure secret (>= 32 chars)
python -c "import secrets; print('INFRASCAN_JWT_SECRET=' + secrets.token_urlsafe(32))" >> .env

# 3. Build and start containers in detached mode
docker compose up -d --build

# 4. Check container status
docker compose ps
```

### 7.2 Service Logs & Health
```bash
# View backend logs
docker compose logs -f backend

# View frontend logs
docker compose logs -f frontend
```

### 7.3 Shutdown, Maintenance & Volume Safety
```bash
# Standard shutdown (PRESERVES volume data, database, and uploads):
docker compose down

# ==============================================================================
# PERMANENT DATA LOSS WARNING:
# Do NOT run 'docker compose down -v' unless you explicitly want to WIPE all data.
# The '-v' / '--volumes' flag PERMANENTLY DESTROYS the 'infrascan_data' volume,
# deleting infrascan.db, all user accounts, uploaded photos, and generated reports!
# ==============================================================================

# Recommended offline backup before volume maintenance:
docker run --rm -v infrascan_data:/data -v $(pwd)/backup:/backup alpine \
    tar czf /backup/infrascan_data_backup.tar.gz -C /data .
```

---

## 8. Local Host Environment Verification Notice

During verification on the Windows development workstation:
* **Docker Availability Check**: The local shell returned `docker: The term 'docker' is not recognized`. Docker Desktop daemon is not installed in the Windows environment (`Test-Path "Docker Desktop.exe" -> False`).
* **Academic Truth in Reporting**:
  * As strictly required by Milestone 4.4 instructions (*"If Docker is unavailable, do not pretend the build or runtime tests passed. Complete the configuration and document the unverified deployment steps"*), we report:
    1. All Dockerfiles (`backend/Dockerfile`, `frontend/Dockerfile`), Nginx reverse-proxy configuration (`frontend/nginx.conf`), `docker-compose.yml`, `.dockerignore`, and `.env.example` have been fully authored, linted, and architected.
    2. The application code was refactored with dynamic environment variable paths (`INFRASCAN_STORAGE_DIR`, etc.) to support seamless containerized execution.
    3. Container build and runtime testing require an environment with Docker engine installed.

---

## 9. Static Verification Results & Physical Model Audit

### 9.1 Static Checks Executed
1. **JWT Secret Enforcement Suite (`scratch/test_jwt_enforcement.py`)**:
   - `Prod Missing Secret`: Blocked startup with `FATAL: INFRASCAN_JWT_SECRET is unset or empty` (**PASSED**).
   - `Prod Short Secret (<32 chars)`: Blocked startup with `FATAL: INFRASCAN_JWT_SECRET is too short (22 characters)` (**PASSED**).
   - `Prod Known Placeholder 1 (`CHANGEME...`)`: Blocked startup with `FATAL: contains a known placeholder value` (**PASSED**).
   - `Prod Known Placeholder 2 (`replace_with...`)`: Blocked startup with `FATAL: contains a known placeholder value` (**PASSED**).
   - `Prod Valid Secret (64 hex chars)`: Permitted production startup cleanly (**PASSED**).
   - `Dev Mode Unset Secret`: Permitted local developer startup with fallback key (**PASSED**).
2. **Dockerignore Build Context Safety**:
   - Verified that `.env`, `.env.*`, `admin_credentials.txt`, `infrascan.db`, `infrascan.sqlite3`, `uploads/`, `results/`, `reports/`, and `scratch/` are strictly excluded from Docker build contexts.
   - Added `frontend/.dockerignore` to protect frontend build context from leaking local `node_modules` or `.env` files.
3. **Docker Compose & Nginx Linting**:
   - `docker-compose.yml` validated via PyYAML; confirms `${INFRASCAN_JWT_SECRET:?Error}` required variable syntax with zero default.
   - `frontend/nginx.conf` validated; confirms `client_max_body_size 50M;` to prevent HTTP 413 upload rejection.

### 9.2 Physical Model Checkpoint Verification
* **Configured Mount Path**: `./models` $\rightarrow$ `/app/models:ro`
* **Physical File on Disk**: `E:\infosys\Internship\InfraScan\models\yolo_best.pt`
* **Verification Status**:
  - `yolo_best.pt` exists physically on disk (size: **19,313,732 bytes** / 18.4 MB).
  - Checkpoint was verified via PyTorch inspection; loads as the baseline 80-class COCO YOLO11s model (`detector.py` prevents COCO objects from altering infrastructure crack geometry).
  - Keras checkpoints `cnn_crack_classifier_best.keras` and `unet_crack500_best.keras` are **not present** on disk; the application activates its verified computer vision texture and adaptive morphological segmentation filters as architected in Milestone 3.

### 9.3 Remaining Limitations
* **Docker Daemon Absent**: The local host does not have Docker Desktop or docker CLI installed. **Docker image builds and container executions remain UNVERIFIED at runtime.**

**Milestone 4.4 Status: CONFIGURATION & DEPLOYMENT READINESS COMPLETE (Runtime Execution Unverified due to Host Docker Absence)**
