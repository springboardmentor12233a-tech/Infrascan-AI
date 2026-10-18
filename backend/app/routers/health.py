"""
health.py – a single GET /health endpoint.

This is the first route we build. It lets us confirm the server is running
before we add any real logic.
"""

from fastapi import APIRouter
from app.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    """
    Returns a simple OK response so you can verify the server is up.
    Open http://localhost:8000/health in your browser to see it.
    """
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "message": "InfraScan API is running",
    }
