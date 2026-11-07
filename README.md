# InfraScan – AI-Powered Crack & Damage Assessment for Civil Infrastructure

## Project Overview

InfraScan explores how computer vision can help identify visible cracks in concrete images. This is a student research prototype, not a structural-safety assessment.

## Project Structure

- frontend/ – React and TypeScript application
- backend/ – FastAPI application and AI-related modules
- notebooks/ – Current repository contains a preprocessing demonstration notebook and its comparison image
- datasets/ and docs/ – Add dataset notes and project documentation here as they are prepared

## Current Status (November 2026)

Milestone 2 implementation is **complete and verified**. All backend services, authentication mechanisms (including RBAC), asset and inspection management, image validation, preprocessing pipelines, and ML evaluation metrics are fully integrated and tested.

- **Test Suite:** 29 automated tests across backend and ML modules running with a **100% pass rate** (`29 passed, 0 failed, 0 warnings`).
- **Frontend Build:** Verified Vite React production build (`npm run build`) succeeding cleanly.
- **Documentation:** Full Milestone 2 technical architecture and evaluation report added in `docs/reports/milestone2_implementation_report.md` and `reports/milestone_2_report.md`.

## Milestone 1: Dataset and Project Foundation

- Selected a balanced 10,000-image Concrete Crack Images for Classification (CCIC) subset: 5,000 cracked and 5,000 uncracked image crops.
- Recorded the selected files in a manifest and prepared 7,000 training, 1,500 validation, and 1,500 test images.
- CCIC has image-level cracked/uncracked labels only; it does not include crack boxes, pixel masks, or physical scale measurements.

## Frontend and Backend Code

### Backend

The backend is a FastAPI application with comprehensive routes for authentication, user management, infrastructure assets, inspections, image upload, quality checking, and preprocessing. The application integrates SQLAlchemy ORM models with SQLite (development/testing) and PostgreSQL (production).

- **Authentication & RBAC:** Multi-role authorization (`admin`, `manager`, `civil_engineer`, `inspector`). Dual OAuth2 form data and JSON body support.
- **Image Pipeline:** Automated EXIF metadata extraction (GPS coordinates, capture timestamps), Laplacian blur variance scoring, brightness analysis, and OpenCV CLAHE contrast enhancement.
- **API Coverage:** Fully verified with 27 backend test cases passing in `backend/tests/`.

### Frontend

The frontend is a React and TypeScript application built with Vite and Tailwind CSS.
- Interactive multi-page application with Dashboard, Assets, Inspections, Image Upload (with drag-and-drop and camera capture), Preprocessing, and Damage Analysis views.
- Verified with zero build or lint errors via `npm run build`.

## Milestone 2: Model Evaluation & Results

- **Classification:** CNN crack classifier achieves **99.69% accuracy**, 99.65% precision, 99.73% recall, and 99.69% F1-score on the 8,000-image validation split.
- **Detection (YOLO):** Multi-class road damage detection achieves **58.60% mAP@50**, 59.70% precision, and 55.10% recall across Crack, Pothole, and Surface Erosion classes.
- **Segmentation (U-Net):** Pixel-level crack segmentation evaluated on 118 verified CrackForest pairs achieves **40.54% IoU**, 57.69% Dice coefficient, and 69.29% pixel precision.
- **Crack Geometry Extraction:** Automated measurement extracts crack pixel area (5,412 px), length (1,845.5 px), and mean width (6.3 px).
- Evaluated and documented in `reports/milestone_2_report.md` and `docs/reports/milestone2_implementation_report.md`.

## Run Locally

### 1. Backend
From the project root:
```powershell
$env:PYTHONPATH = "backend;."
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive API documentation: `http://127.0.0.1:8000/docs`

### 2. Frontend
```powershell
cd frontend
npm install
npm run dev
```
Access the application at: `http://localhost:5173`

### 3. Run Automated Tests
```powershell
$env:PYTHONPATH = "backend;."
.\.venv\Scripts\python.exe -m pytest backend\tests ml\test_milestone2.py -v
```
