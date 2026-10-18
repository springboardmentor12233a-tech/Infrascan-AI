from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional

from app.database import get_db
from app.models.infrastructure_asset import InfrastructureAsset, AssetType
from app.models.user import User
from app.schemas.asset_inspection import AssetCreate, AssetUpdate, AssetOut, AssetListResponse
from app.core.deps import get_current_user, require_roles
from app.services.audit import log_action

router = APIRouter(tags=["Assets"])


@router.get("/", response_model=AssetListResponse)
def list_assets(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by name or asset code"),
    asset_type: Optional[AssetType] = Query(None, description="Filter by asset type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List infrastructure assets with pagination, search, and type filtering.
    All authenticated roles can view assets.
    """
    query = db.query(InfrastructureAsset)

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                InfrastructureAsset.name.ilike(pattern),
                InfrastructureAsset.asset_code.ilike(pattern)
            )
        )

    if asset_type:
        query = query.filter(InfrastructureAsset.type == asset_type)

    total = query.count()
    offset = (page - 1) * size
    items = query.order_by(InfrastructureAsset.id.desc()).offset(offset).limit(size).all()

    return AssetListResponse(total=total, page=page, size=size, items=items)


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Infrastructure asset not found"
        )
    return asset


@router.post("/", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
def create_asset(
    asset_in: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Administrator", "Infrastructure Manager"))
):
    # Check unique code
    existing = db.query(InfrastructureAsset).filter(InfrastructureAsset.asset_code == asset_in.asset_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset with code '{asset_in.asset_code}' already exists."
        )

    asset = InfrastructureAsset(**asset_in.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)

    log_action(db, action="create", entity="asset", entity_id=str(asset.id), user_id=current_user.id)
    return asset


@router.put("/{asset_id}", response_model=AssetOut)
def update_asset(
    asset_id: int,
    asset_in: AssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Administrator", "Infrastructure Manager"))
):
    asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Infrastructure asset not found"
        )

    update_data = asset_in.model_dump(exclude_unset=True)
    if "asset_code" in update_data and update_data["asset_code"] != asset.asset_code:
        existing = db.query(InfrastructureAsset).filter(InfrastructureAsset.asset_code == update_data["asset_code"]).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Asset with code '{update_data['asset_code']}' already exists."
            )

    for field, val in update_data.items():
        setattr(asset, field, val)

    db.commit()
    db.refresh(asset)

    log_action(db, action="update", entity="asset", entity_id=str(asset.id), user_id=current_user.id)
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Administrator", "Infrastructure Manager"))
):
    asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Infrastructure asset not found"
        )

    db.delete(asset)
    db.commit()

    log_action(db, action="delete", entity="asset", entity_id=str(asset_id), user_id=current_user.id)
    return None
