from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.assets import router as assets_router
from app.routers.inspections import router as inspections_router
from app.routers.images import router as images_router
from app.routers.analysis import router as analysis_router
from app.routers.severity import router as severity_router
from app.routers.explanations import router as explanations_router
from app.routers.map import router as map_router
from app.routers.reports import router as reports_router
from app.routers.notifications import router as notifications_router
from app.routers.models import router as models_router
from app.routers.jobs import router as jobs_router
from app.routers.monitoring import router as monitoring_router
from app.routers.events import router as events_router
from app.routers.maintenance import router as maintenance_router
from app.routers.comparisons import router as comparisons_router
from app.routers.dashboard import router as dashboard_router

__all__ = [
    "auth_router",
    "users_router",
    "assets_router",
    "inspections_router",
    "images_router",
    "analysis_router",
    "severity_router",
    "explanations_router",
    "map_router",
    "reports_router",
    "notifications_router",
    "models_router",
    "jobs_router",
    "monitoring_router",
    "events_router",
    "maintenance_router",
    "comparisons_router",
    "dashboard_router",
]
