"""Counts for the dashboard. These are live database counts, not placeholders."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.image_analysis import ImageAnalysis
from app.models.infrastructure_asset import InfrastructureAsset
from app.models.inspection import Inspection
from app.models.inspection_image import InspectionImage
from app.models.user import User
from app.schemas.analysis import DashboardStats

router = APIRouter(tags=["Stats"])


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return DashboardStats(
        assets=db.query(InfrastructureAsset).count(),
        inspections=db.query(Inspection).count(),
        images=db.query(InspectionImage).count(),
        analyses=db.query(ImageAnalysis).count(),
    )
