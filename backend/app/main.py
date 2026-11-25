import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
import app.models  # Register models with SQLAlchemy Base
from app.routers import (
    analysis_router,
    assets_router,
    auth_router,
    images_router,
    inspections_router,
    severity_router,
    explanations_router,
    map_router,
    users_router,
    reports_router,
    notifications_router,
    models_router,
    jobs_router,
    monitoring_router,
    events_router,
    maintenance_router,
    comparisons_router,
    dashboard_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Only run DB migrations on live startup, not during isolated unit tests
    if os.getenv("TESTING") != "1":
        Base.metadata.create_all(bind=engine)
        try:
            from scripts.migrate_preprocess import run_migration
            run_migration()
        except Exception as e:
            print(f"Warning: Migration check encountered an issue: {e}")
        try:
            from scripts.migrate_severity import run_migration as run_severity_migration
            run_severity_migration()
        except Exception as e:
            print(f"Warning: Severity migration check encountered an issue: {e}")
        try:
            from scripts.migrate_explanations import run_migration as run_explanations_migration
            run_explanations_migration()
        except Exception as e:
            print(f"Warning: Explanations migration check encountered an issue: {e}")
        try:
            from scripts.migrate_m3_part2 import run_migration as run_m3_part2_migration
            run_m3_part2_migration()
        except Exception as e:
            print(f"Warning: M3 Part 2 migration check encountered an issue: {e}")
        try:
            from scripts.migrate_phase1 import run_migration as run_phase1_migration
            run_phase1_migration()
        except Exception as e:
            print(f"Warning: Phase 1 migration check encountered an issue: {e}")
        try:
            from scripts.migrate_phase2 import run_migration as run_phase2_migration
            run_phase2_migration()
        except Exception as e:
            print(f"Warning: Phase 2 migration check encountered an issue: {e}")
        try:
            from scripts.migrate_phase3 import run_migration as run_phase3_migration
            run_phase3_migration()
        except Exception as e:
            print(f"Warning: Phase 3 migration check encountered an issue: {e}")
        try:
            from scripts.migrate_phase4 import run_migration as run_phase4_migration
            run_phase4_migration()
        except Exception as e:
            print(f"Warning: Phase 4 migration check encountered an issue: {e}")
        try:
            from scripts.migrate_phase5 import run_migration as run_phase5_migration
            run_phase5_migration()
        except Exception as e:
            print(f"Warning: Phase 5 migration check encountered an issue: {e}")
        try:
            from scripts.migrate_phase2_events import run_migration as run_phase2_events_migration
            run_phase2_events_migration()
        except Exception as e:
            print(f"Warning: Phase 2 events migration check encountered an issue: {e}")

        # Start PostgreSQL LISTEN/NOTIFY background thread if running on PostgreSQL
        try:
            from app.services.event_service import start_pg_listener
            start_pg_listener()
        except Exception as e:
            print(f"Notice (pg_listener): {e}")
    yield


# Initialize FastAPI application
app = FastAPI(
    title="InfraScan API",
    description="AI crack detection web app backend with authentication and RBAC",
    version="0.1.0",
    lifespan=lifespan,
)

# Allowed origins for frontend communication
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data: blob:; script-src 'self'; style-src 'self' 'unsafe-inline';"
    return response

# Prometheus request tracking middleware
from app.routers.monitoring import record_request_metric
import time
import uuid

@app.middleware("http")
async def track_requests_middleware(request, call_next):
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    t0 = time.time()
    response = await call_next(request)
    duration = time.time() - t0
    record_request_metric(request.method, request.url.path, response.status_code, duration)
    response.headers["X-Request-ID"] = req_id
    return response

# Mount API routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(assets_router)
app.include_router(inspections_router)
app.include_router(images_router)
app.include_router(analysis_router)
app.include_router(severity_router)
app.include_router(explanations_router)
app.include_router(map_router)
app.include_router(reports_router)
app.include_router(notifications_router)
app.include_router(models_router)
app.include_router(jobs_router)
app.include_router(monitoring_router)
app.include_router(events_router)
app.include_router(maintenance_router)
app.include_router(comparisons_router)
app.include_router(dashboard_router)


# Health check endpoint
@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
