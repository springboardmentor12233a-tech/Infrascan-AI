import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine, Base, SessionLocal
import app.models  # Registers all models

from app.routers.health import router as health_router
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.assets import router as assets_router
from app.routers.inspections import router as inspections_router
from app.routers.images import router as images_router

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "AI-powered crack and damage assessment for civil infrastructure.\n\n"
        "⚠️ **Disclaimer**: AI results are decision support, "
        "not a structural safety evaluation."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Upload directory setup
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    print(f"[OK] {settings.APP_NAME} started - DB tables ready")

    from app.services.seed import seed_roles
    db = SessionLocal()
    try:
        seed_roles(db)
    finally:
        db.close()


# Routers
app.include_router(health_router)
app.include_router(auth_router, prefix="/auth")
app.include_router(users_router, prefix="/users")
app.include_router(assets_router, prefix="/assets")
app.include_router(inspections_router, prefix="/inspections")
app.include_router(images_router)
