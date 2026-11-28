from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.models import InfrastructureAsset, User
from app.schemas.schemas import AssetCreate, AssetUpdate, AssetOut

router = APIRouter(prefix="/assets", tags=["Infrastructure Assets"])


@router.post("", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
def create_asset(
    payload: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "Engineer", "Inspector")),
):
    if db.query(InfrastructureAsset).filter(InfrastructureAsset.asset_code == payload.asset_code).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Asset code already exists")
    asset = InfrastructureAsset(**payload.model_dump(), created_by=current_user.id)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.get("", response_model=list[AssetOut])
def list_assets(
    q: str | None = Query(default=None),
    infrastructure_type: str | None = Query(default=None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(InfrastructureAsset).filter(InfrastructureAsset.asset_status != "Archived")
    if q:
        query = query.filter(InfrastructureAsset.name.ilike(f"%{q}%"))
    if infrastructure_type:
        query = query.filter(InfrastructureAsset.infrastructure_type == infrastructure_type)
    return query.offset(skip).limit(limit).all()


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return asset


@router.patch("/{asset_id}", response_model=AssetOut)
def update_asset(
    asset_id: str,
    payload: AssetUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Engineer")),
):
    asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(asset, k, v)
    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Engineer")),
):
    asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    asset.asset_status = "Archived"
    db.commit()

