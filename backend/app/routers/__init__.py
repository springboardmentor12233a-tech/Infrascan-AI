from .auth import router as auth_router
from .users import router as users_router
from .assets import router as assets_router
from .inspections import router as inspections_router
from .images import router as images_router
from .analysis import router as analysis_router
from .progression import router as progression_router
from .maintenance import router as maintenance_router
from .reports import router as reports_router
from .notifications import router as notifications_router
from .dashboard import router as dashboard_router

__all__ = [
    "auth_router",
    "users_router",
    "assets_router",
    "inspections_router",
    "images_router",
    "analysis_router",
    "progression_router",
    "maintenance_router",
    "reports_router",
    "notifications_router",
    "dashboard_router",
]
