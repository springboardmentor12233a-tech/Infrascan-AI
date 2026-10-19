from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
import app.models  # Register models with SQLAlchemy Base
from app.routers import (
    assets_router,
    auth_router,
    images_router,
    inspections_router,
    users_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all database tables on application startup
    Base.metadata.create_all(bind=engine)
    try:
        from scripts.migrate_preprocess import run_migration
        run_migration()
    except Exception as e:
        print(f"Warning: Migration check encountered an issue: {e}")
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

# Mount API routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(assets_router)
app.include_router(inspections_router)
app.include_router(images_router)


# Health check endpoint
@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
