from fastapi import APIRouter
from app.api.v1.endpoints import auth, assets, inspections, images, analysis

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(assets.router)
api_router.include_router(inspections.router)
api_router.include_router(images.router)
api_router.include_router(analysis.router)

