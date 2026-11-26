from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Asset
from schemas import AssetCreate, AssetResponse

router = APIRouter(prefix="/api/assets", tags=["assets"])

@router.get("/", response_model=List[AssetResponse])
def get_assets(db: Session = Depends(get_db)):
    return db.query(Asset).order_by(Asset.name).all()

@router.post("/", response_model=AssetResponse)
def create_asset(asset: AssetCreate, db: Session = Depends(get_db)):
    db_asset = Asset(**asset.dict())
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset

@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset_detail(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset
