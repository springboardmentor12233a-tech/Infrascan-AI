from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.asset import InfrastructureAsset
from app.models.inspection import Inspection
from app.models.user import User
from app.schemas.asset import (
    AssetCreate,
    AssetDetailResponse,
    AssetListResponse,
    AssetResponse,
    AssetUpdate,
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    GeoJSONGeometry,
)
from app.schemas.inspection import InspectionSummaryResponse
from app.services.audit import create_audit_log

router = APIRouter(prefix="/assets", tags=["Infrastructure Assets"])


# Helper function to enrich an asset with its last inspection date
def enrich_asset_response(asset: InfrastructureAsset, db: Session) -> AssetResponse:
    last_insp = (
        db.query(func.max(Inspection.inspection_date))
        .filter(Inspection.asset_id == asset.asset_id)
        .scalar()
    )
    res = AssetResponse.model_validate(asset)
    res.last_inspection_date = last_insp
    return res


# 1. POST /assets - Create new asset (admin, manager)
@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(
    asset_data: AssetCreate,
    request: Request,
    current_user: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    """Create a new infrastructure asset (Admin, Manager)."""
    new_asset = InfrastructureAsset(
        **asset_data.model_dump(),
        created_by=current_user.user_id,
    )
    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)

    # Record audit log
    client_ip = request.client.host if request.client else None
    create_audit_log(
        db=db,
        action="create_asset",
        user_id=current_user.user_id,
        entity_type="asset",
        entity_id=str(new_asset.asset_id),
        ip_address=client_ip,
    )

    return enrich_asset_response(new_asset, db)


# 2. GET /assets - Paginated list of assets with search & filters (any logged-in user)
@router.get("", response_model=AssetListResponse)
def list_assets(
    search: Optional[str] = Query(None, description="Search by asset name"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type"),
    material_type: Optional[str] = Query(None, description="Filter by material type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List assets with pagination, search, and type filters."""
    query = db.query(InfrastructureAsset)

    if search:
        query = query.filter(InfrastructureAsset.name.ilike(f"%{search.strip()}%"))
    if asset_type:
        query = query.filter(InfrastructureAsset.asset_type == asset_type)
    if material_type:
        query = query.filter(InfrastructureAsset.material_type == material_type)

    total = query.count()
    offset = (page - 1) * page_size
    assets = query.order_by(InfrastructureAsset.asset_id.asc()).offset(offset).limit(page_size).all()

    items = [enrich_asset_response(a, db) for a in assets]
    return AssetListResponse(items=items, total=total, page=page, page_size=page_size)


# 3. GET /assets/geojson - GeoJSON FeatureCollection for map (MUST BE BEFORE /{id})
@router.get("/geojson", response_model=GeoJSONFeatureCollection)
def get_assets_geojson(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all assets as a GeoJSON FeatureCollection (coordinates: [lon, lat])."""
    assets = db.query(InfrastructureAsset).all()
    features: List[GeoJSONFeature] = []

    for a in assets:
        feat = GeoJSONFeature(
            type="Feature",
            geometry=GeoJSONGeometry(
                type="Point",
                coordinates=[a.longitude, a.latitude],  # GeoJSON standard: [longitude, latitude]
            ),
            properties={
                "id": a.asset_id,
                "name": a.name,
                "type": a.asset_type,
                "material": a.material_type,
                "importance": a.importance_level,
                "address": a.address,
            },
        )
        features.append(feat)

    return GeoJSONFeatureCollection(features=features)


# 4. GET /assets/{id} - Asset details with inspection history (any logged-in user)
@router.get("/{id}", response_model=AssetDetailResponse)
def get_asset_detail(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get single asset by ID along with its list of inspections."""
    asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.asset_id == id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    # Fetch inspections for this asset
    inspections = (
        db.query(Inspection)
        .filter(Inspection.asset_id == id)
        .order_by(desc(Inspection.inspection_date))
        .all()
    )

    last_insp = inspections[0].inspection_date if inspections else None

    # Format inspection summary items
    insp_summaries = []
    for insp in inspections:
        summary = InspectionSummaryResponse(
            inspection_id=insp.inspection_id,
            inspector_id=insp.inspector_id,
            inspector_name=insp.inspector.full_name if insp.inspector else None,
            inspection_date=insp.inspection_date,
            status=insp.status,
            created_at=insp.created_at,
        )
        insp_summaries.append(summary)

    asset_dict = AssetResponse.model_validate(asset).model_dump()
    asset_dict["last_inspection_date"] = last_insp
    asset_dict["inspections"] = insp_summaries

    return AssetDetailResponse(**asset_dict)


# 5. PUT /assets/{id} - Update asset (admin, manager)
@router.put("/{id}", response_model=AssetResponse)
def update_asset(
    id: int,
    asset_data: AssetUpdate,
    request: Request,
    current_user: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    """Update an existing infrastructure asset (Admin, Manager)."""
    asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.asset_id == id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    for key, value in asset_data.model_dump().items():
        setattr(asset, key, value)

    db.commit()
    db.refresh(asset)

    # Record audit log
    client_ip = request.client.host if request.client else None
    create_audit_log(
        db=db,
        action="update_asset",
        user_id=current_user.user_id,
        entity_type="asset",
        entity_id=str(asset.asset_id),
        ip_address=client_ip,
    )

    return enrich_asset_response(asset, db)


# 6. DELETE /assets/{id} - Delete asset (admin only, blocked if inspections exist)
@router.delete("/{id}")
def delete_asset(
    id: int,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Delete an asset (Admin only). Refuses deletion if inspections exist."""
    asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.asset_id == id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    # Check if any inspections are associated with this asset
    inspection_count = db.query(Inspection).filter(Inspection.asset_id == id).count()
    if inspection_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete asset: {inspection_count} inspection record(s) exist for this asset.",
        )

    db.delete(asset)
    db.commit()

    # Record audit log
    client_ip = request.client.host if request.client else None
    create_audit_log(
        db=db,
        action="delete_asset",
        user_id=current_user.user_id,
        entity_type="asset",
        entity_id=str(id),
        ip_address=client_ip,
    )

    return {"message": "Asset deleted successfully"}
