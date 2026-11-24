"""
InfraScan FastAPI Application Entry Point.

AI-Powered Crack & Damage Assessment for Civil Infrastructure.
Serves classification, pixel segmentation, damage assessment, PDF reporting, and interactive dashboard UI.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.database import init_db
from backend.routes.auth import router as auth_router
from backend.routes.inspection import router as inspection_router
from backend.routes.prediction import router as prediction_router
from backend.schemas.prediction import HealthResponse
from backend.services.auth import decode_access_token
from backend.services.classifier import classifier_service
from backend.services.segmenter import segmenter_service

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"
PREDICTIONS_DIR = PROJECT_ROOT / "outputs" / "predictions"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"

# Ensure runtime directories exist
STATIC_DIR.mkdir(parents=True, exist_ok=True)
PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
(PREDICTIONS_DIR / "masks").mkdir(parents=True, exist_ok=True)
(PREDICTIONS_DIR / "overlays").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "uploads").mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Preloads AI models and initializes database on server startup."""
    print("[Startup] Initializing InfraScan database...")
    init_db()

    print("[Startup] Initializing InfraScan AI models...")
    try:
        classifier_service.load_model()
    except Exception as exc:
        print(f"[Startup Warning] Could not preload classifier: {exc}")

    try:
        segmenter_service.load_model()
    except Exception as exc:
        print(f"[Startup Warning] Could not preload segmenter: {exc}")

    print("[Startup] InfraScan models & database initialized and ready.")
    yield
    print("[Shutdown] InfraScan API shutting down.")


app = FastAPI(
    title="InfraScan API",
    description="AI-Powered Crack & Damage Assessment for Civil Infrastructure using Deep Learning and Computer Vision.",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Mount Static Directories for serving prediction masks, overlays, uploads, and reports
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/outputs/predictions", StaticFiles(directory=str(PREDICTIONS_DIR)), name="predictions")
app.mount("/outputs/reports", StaticFiles(directory=str(REPORTS_DIR)), name="reports")

# Register Modular Routers
app.include_router(auth_router)
app.include_router(prediction_router)
app.include_router(inspection_router)


def _is_authenticated(request: Request) -> bool:
    """Checks whether the request carries a valid authentication token via cookie or header."""
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get("infrascan_token")
    if not token:
        return False
    payload = decode_access_token(token)
    return payload is not None and "sub" in payload


@app.get(
    "/login",
    response_class=HTMLResponse,
    tags=["Authentication"],
    summary="User Login & Registration Page"
)
@app.get("/register", response_class=HTMLResponse, tags=["Authentication"], include_in_schema=False)
@app.get("/forgot-password", response_class=HTMLResponse, tags=["Authentication"], include_in_schema=False)
@app.get("/reset-password", response_class=HTMLResponse, tags=["Authentication"], include_in_schema=False)
def login_view():
    """Serves the portal login, registration, and password recovery interface."""
    login_html = TEMPLATES_DIR / "login.html"
    return FileResponse(str(login_html), media_type="text/html")


@app.get(
    "/",
    tags=["System"],
    summary="Application Entry Point",
    description="Serves login page to unauthenticated visitors, dashboard to authenticated users, or JSON metadata for API clients."
)
def home(request: Request):
    """Returns HTML dashboard if authenticated, login page if unauthenticated browser, or JSON for API clients."""
    accept_header = request.headers.get("accept", "")
    
    # If request is from browser navigation
    if "text/html" in accept_header:
        if _is_authenticated(request):
            return FileResponse(str(TEMPLATES_DIR / "index.html"), media_type="text/html")
        return RedirectResponse(url="/login", status_code=302)

    # Standard API root JSON
    return {
        "project": "InfraScan",
        "tagline": "AI-Powered Crack & Damage Assessment for Civil Infrastructure",
        "version": "2.0.0",
        "status": "online",
        "documentation": "/docs",
        "dashboard": "/dashboard",
        "auth": {
            "login": "/login",
            "api_login": "/api/auth/login",
            "api_register": "/api/auth/register",
            "api_me": "/api/auth/me"
        },
        "endpoints": {
            "health": "/health",
            "classify": "/predict/classify",
            "segment": "/predict/segment",
            "combined": "/predict",
            "stats": "/api/dashboard/stats",
            "inspections": "/api/inspections",
            "csv_export": "/api/inspections/export/csv"
        }
    }


@app.get(
    "/dashboard",
    response_class=HTMLResponse,
    tags=["System"],
    summary="Interactive Web Dashboard UI"
)
def dashboard_view(request: Request):
    """Protected dashboard view: serves dashboard if authenticated, else redirects to /login."""
    if _is_authenticated(request):
        return FileResponse(str(TEMPLATES_DIR / "index.html"), media_type="text/html")
    return RedirectResponse(url="/login", status_code=302)


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="System Health & Model Readiness Check",
    description="Reports operational status of the API and verifies that both deep learning models are active in memory."
)
def health_check():
    return HealthResponse(
        status="healthy",
        classification_model_loaded=classifier_service.is_loaded(),
        segmentation_model_loaded=segmenter_service.is_loaded()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
