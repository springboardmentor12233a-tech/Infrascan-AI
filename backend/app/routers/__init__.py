from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.assets import router as assets_router
from app.routers.inspections import router as inspections_router
from app.routers.images import router as images_router

__all__ = [
    "auth_router",
    "users_router",
    "assets_router",
    "inspections_router",
    "images_router",
]
