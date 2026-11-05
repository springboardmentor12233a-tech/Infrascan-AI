import io
import json
import os
import uuid

import threading
import cv2
import numpy as np
from fastapi.responses import FileResponse

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None
from pathlib import Path
from PIL import Image as PILImage, ImageEnhance, ImageFilter, ImageOps
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .auth import current_user, hash_password, make_token, verify_password
from .db import Base, engine, get_db
from .models import Image, InfrastructureAsset, Inspection, User
from .legacy_schemas import AssetIn, AssetOut, AuthIn, InspectionIn, InspectionOut, PasswordIn, TokenOut, UserOut

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

YOLO_MODEL_PATH = Path(__file__).resolve().parents[2] / "runs" / "road_damage" / "yolo11n_initial" / "weights" / "best.pt"
_yolo_model = None
_yolo_model_lock = threading.Lock()
_yolo_annotated_paths: dict[int, Path] = {}


def get_yolo_model():
    global _yolo_model
    if _yolo_model is not None:
        return _yolo_model
    if YOLO is None:
        raise HTTPException(503, "Ultralytics YOLO is not installed")
    if not YOLO_MODEL_PATH.is_file():
        raise HTTPException(503, f"YOLO model file not found: {YOLO_MODEL_PATH}")
    with _yolo_model_lock:
        if _yolo_model is None:
            try:
                _yolo_model = YOLO(str(YOLO_MODEL_PATH))
            except Exception as exc:
                raise HTTPException(503, "Unable to load the YOLO model") from exc
    return _yolo_model


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
    return db.query(InfrastructureAsset).order_by(InfrastructureAsset.created_at.desc()).all()

@app.post("/api/assets", response_model=AssetOut, status_code=201)
def create_asset(payload: AssetIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if db.query(InfrastructureAsset).filter(InfrastructureAsset.asset_id == payload.asset_id).first():
        raise HTTPException(409, "Asset ID already exists")
    asset = InfrastructureAsset(**payload.model_dump()); db.add(asset); db.commit(); db.refresh(asset)
    return asset

@app.put("/api/assets/{asset_id}", response_model=AssetOut)
def update_asset(asset_id: str, payload: AssetIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.asset_id == asset_id).first()
    if not asset: raise HTTPException(404, "Asset not found")
    duplicate = db.query(InfrastructureAsset).filter(InfrastructureAsset.asset_id == payload.asset_id, InfrastructureAsset.asset_id != asset.asset_id).first()
    if duplicate: raise HTTPException(409, "Asset ID already exists")
    for key, value in payload.model_dump().items(): setattr(asset, key, value)
    db.commit(); db.refresh(asset); return asset

@app.delete("/api/assets/{asset_id}", status_code=204)
def delete_asset(asset_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.asset_id == asset_id).first()
    if not asset: raise HTTPException(404, "Asset not found")
    db.delete(asset); db.commit()

@app.post("/api/inspections", response_model=InspectionOut, status_code=201)
def create_inspection(payload: InspectionIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not db.get(InfrastructureAsset, payload.asset_id): raise HTTPException(404, "Asset not found")
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


@app.post("/api/images/{image_id}/analyze/yolo")
def analyze_yolo(image_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    record = db.get(Image, image_id)
    if not record:
        raise HTTPException(404, "Image not found")

    image_path = Path(record.original_path).resolve()
    try:
        image_path.relative_to(MEDIA.resolve())
    except ValueError:
        raise HTTPException(400, "Image is outside the configured media directory")

    if not image_path.is_file():
        raise HTTPException(404, "Uploaded image file not found")

    model = get_yolo_model()
    try:
        predictions = model.predict(source=str(image_path), device="cpu", verbose=False)
    except Exception as exc:
        raise HTTPException(500, "YOLO prediction failed") from exc

    if not predictions:
        raise HTTPException(500, "YOLO returned no prediction result")

    prediction = predictions[0]
    names = prediction.names
    detections = []
    boxes = prediction.boxes

    if boxes is not None:
        coordinates = boxes.xyxy.detach().cpu().numpy()
        confidences = boxes.conf.detach().cpu().numpy()
        class_ids = boxes.cls.detach().cpu().numpy().astype(int)

        for box, confidence, class_id in zip(coordinates, confidences, class_ids):
            class_name = names[class_id] if isinstance(names, (list, tuple)) else names.get(class_id, str(class_id))
            detections.append({
                "class_id": int(class_id),
                "class_name": str(class_name),
                "confidence": float(confidence),
                "bounding_box": {
                    "x1": float(box[0]),
                    "y1": float(box[1]),
                    "x2": float(box[2]),
                    "y2": float(box[3]),
                },
            })

    output_path = MEDIA / f"yolo_{image_id}_{uuid.uuid4().hex}.jpg"
    if not cv2.imwrite(str(output_path), np.asarray(prediction.plot())):
        raise HTTPException(500, "Unable to save annotated YOLO prediction image")

    _yolo_annotated_paths[image_id] = output_path

    return {
        "image_id": image_id,
        "model": YOLO_MODEL_PATH.name,
        "total_detections": len(detections),
        "detections": detections,
        "annotated_image_url": f"/api/images/{image_id}/analyze/yolo/annotated",
    }


@app.get("/api/images/{image_id}/analyze/yolo/annotated")
def get_annotated_yolo_image(image_id: int, user: User = Depends(current_user)):
    output_path = _yolo_annotated_paths.get(image_id)
    if output_path is None or not output_path.is_file():
        raise HTTPException(404, "Annotated YOLO image not found; run analysis first")

    try:
        output_path.resolve().relative_to(MEDIA.resolve())
    except ValueError as exc:
        raise HTTPException(500, "Annotated image path is outside the media directory") from exc

    return FileResponse(output_path, media_type="image/jpeg")
