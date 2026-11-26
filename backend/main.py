import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import engine, Base
from routers import health, assets, inspection, dashboard, analytics, auth, admin

# Create database tables
Base.metadata.create_all(bind=engine)

# Create storage directories
BASE_STORAGE = os.environ.get(
    "INFRASCAN_STORAGE_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

UPLOAD_DIR = os.environ.get(
    "INFRASCAN_UPLOAD_DIR",
    os.path.join(BASE_STORAGE, "uploads")
)

RESULTS_DIR = os.environ.get(
    "INFRASCAN_RESULTS_DIR",
    os.path.join(BASE_STORAGE, "results")
)

REPORTS_DIR = os.environ.get(
    "INFRASCAN_REPORTS_DIR",
    os.path.join(BASE_STORAGE, "reports")
)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

app = FastAPI(
    title="InfraScan — AI Civil Infrastructure Inspection Platform",
    description="Backend API for crack classification, detection, segmentation, damage severity, and maintenance prioritization with Role-Based Access Control.",
    version="2.0.0"
)

# CORS setup for React Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for images & reports
app.mount("/static/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/static/results", StaticFiles(directory=RESULTS_DIR), name="results")

# Routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(health.router)
app.include_router(assets.router)
app.include_router(inspection.router)
app.include_router(dashboard.router)
app.include_router(analytics.router)

@app.get("/")
def root():
    return {
        "message": "Welcome to InfraScan AI Infrastructure Inspection Platform API",
        "documentation": "/docs",
        "health": "/api/health",
        "version": "2.0.0 (YOLO11s + RBAC Enabled)"
    }
