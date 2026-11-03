import io
import json
import os
import uuid
from pathlib import Path
from PIL import Image as PILImage, ImageEnhance, ImageFilter, ImageOps
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .auth import current_user, hash_password, make_token, verify_password
from .db import Base, engine, get_db
from .models import Asset, Image, Inspection, User
from .schemas import AssetIn, AssetOut, AuthIn, InspectionIn, InspectionOut, PasswordIn, TokenOut, UserOut

Base.metadata.create_all(bind=engine)
app = FastAPI(title="InfraScan API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:4173,http://127.0.0.1:5173,http://127.0.0.1:4173",
    ).split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
MEDIA = Path(os.getenv("INFRASCAN_MEDIA_DIR", Path(__file__).resolve().parent.parent / "media"))
MEDIA.mkdir(parents=True, exist_ok=True)
MAX_BYTES = 25 * 1024 * 1024
ALLOWED = {"image/jpeg", "image/png"}

@app.get("/health")
def health():
    return {"status": "ok", "database": os.getenv("DATABASE_URL", "sqlite:///./infrascan.db").split("://")[0]}

@app.post("/api/auth/register", response_model=TokenOut, status_code=201)
def register(payload: AuthIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(409, "Email already registered")
    user = User(name=payload.name or payload.email.split("@")[0], email=payload.email.lower(), password_hash=hash_password(payload.password))
    db.add(user); db.commit(); db.refresh(user)
    return {"access_token": make_token(user), "user": user}

@app.post("/api/auth/login", response_model=TokenOut)
def login(payload: AuthIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return {"access_token": make_token(user), "user": user}

@app.get("/api/auth/profile", response_model=UserOut)
def profile(user: User = Depends(current_user)):
    return user

@app.post("/api/auth/password", response_model=UserOut)
def change_password(payload: PasswordIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = hash_password(payload.new_password); db.commit(); db.refresh(user)
    return user

@app.get("/api/assets", response_model=list[AssetOut])
def list_assets(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return db.query(Asset).order_by(Asset.created_at.desc()).all()

@app.post("/api/assets", response_model=AssetOut, status_code=201)
def create_asset(payload: AssetIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if db.query(Asset).filter(Asset.asset_id == payload.asset_id).first():
        raise HTTPException(409, "Asset ID already exists")
    asset = Asset(**payload.model_dump()); db.add(asset); db.commit(); db.refresh(asset)
    return asset

@app.put("/api/assets/{asset_id}", response_model=AssetOut)
def update_asset(asset_id: str, payload: AssetIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    asset = db.query(Asset).filter(Asset.asset_id == asset_id).first()
    if not asset: raise HTTPException(404, "Asset not found")
    duplicate = db.query(Asset).filter(Asset.asset_id == payload.asset_id, Asset.id != asset.id).first()
    if duplicate: raise HTTPException(409, "Asset ID already exists")
    for key, value in payload.model_dump().items(): setattr(asset, key, value)
    db.commit(); db.refresh(asset); return asset

@app.delete("/api/assets/{asset_id}", status_code=204)
def delete_asset(asset_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    asset = db.query(Asset).filter(Asset.asset_id == asset_id).first()
    if not asset: raise HTTPException(404, "Asset not found")
    db.delete(asset); db.commit()

@app.post("/api/inspections", response_model=InspectionOut, status_code=201)
def create_inspection(payload: InspectionIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not db.get(Asset, payload.asset_id): raise HTTPException(404, "Asset not found")
    inspection = Inspection(**payload.model_dump()); db.add(inspection); db.commit(); db.refresh(inspection); return inspection

@app.get("/api/inspections", response_model=list[InspectionOut])
def list_inspections(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return db.query(Inspection).order_by(Inspection.created_at.desc()).all()

def read_validated(upload: UploadFile) -> tuple[bytes, PILImage.Image]:
    if upload.content_type not in ALLOWED:
        raise HTTPException(415, "Only JPG/JPEG and PNG images are supported")
    raw = upload.file.read()
    if len(raw) > MAX_BYTES: raise HTTPException(413, "Image exceeds 25 MB limit")
    try: image = PILImage.open(io.BytesIO(raw)); image.load()
    except Exception as exc: raise HTTPException(400, "Invalid image file") from exc
    if image.width < 1024 or image.height < 1024: raise HTTPException(422, "Image must be at least 1024x1024 pixels")
    return raw, ImageOps.exif_transpose(image).convert("RGB")

@app.post("/api/images/upload")
def upload_image(file: UploadFile = File(...), inspection_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(current_user)):
    raw, image = read_validated(file)
    if inspection_id and not db.get(Inspection, inspection_id): raise HTTPException(404, "Inspection not found")
    key = f"{uuid.uuid4().hex}_{Path(file.filename or 'upload.jpg').name}"
    path = MEDIA / key; path.write_bytes(raw)
    record = Image(inspection_id=inspection_id, original_filename=file.filename or key, original_path=str(path), content_type=file.content_type or "image/jpeg", width=image.width, height=image.height, size_bytes=len(raw))
    db.add(record); db.commit(); db.refresh(record)
    return {"id": record.id, "filename": record.original_filename, "width": image.width, "height": image.height, "size_bytes": len(raw), "message": "validated and stored"}

@app.post("/api/images/{image_id}/preprocess")
def preprocess_image(image_id: int, resize: int = 1024, brightness: float = 1.0, contrast: float = 1.0, db: Session = Depends(get_db), user: User = Depends(current_user)):
    record = db.get(Image, image_id)
    if not record: raise HTTPException(404, "Image not found")
    image = PILImage.open(record.original_path).convert("RGB")
    processed = ImageOps.fit(image, (resize, resize))
    processed = ImageEnhance.Brightness(processed).enhance(max(0.1, min(brightness, 3)))
    processed = ImageEnhance.Contrast(processed).enhance(max(0.1, min(contrast, 3))).filter(ImageFilter.MedianFilter(size=3)).filter(ImageFilter.SHARPEN)
    out = MEDIA / f"processed_{Path(record.original_path).name}.jpg"; processed.save(out, quality=90)
    record.processed_path = str(out); record.preprocessing_metadata = json.dumps({"resize": [resize, resize], "brightness": brightness, "contrast": contrast, "noise_reduction": "median-3", "sharpening": "Pillow SHARPEN", "original_preserved": True})
    db.commit()
    return {"image_id": image_id, "processed_path": str(out), "metadata": json.loads(record.preprocessing_metadata)}
