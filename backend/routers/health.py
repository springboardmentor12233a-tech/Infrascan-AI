
from fastapi import APIRouter

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/")
def health_check():
    return {
        "status": "online",
        "service": "InfraScan AI Civil Infrastructure Inspection API",
        "version": "1.0.0",
        "message": "Backend API is running and responding to requests."
    }
