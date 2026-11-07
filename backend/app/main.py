import io
import hashlib
import json
import os
import uuid
import threading
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

from PIL import Image as PILImage, ImageEnhance, ImageFilter, ImageOps

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from sqlalchemy import text
from sqlalchemy.orm import Session

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

from .auth import current_user, hash_password, make_token, verify_password
from .services.security import create_access_token
from .db import Base, engine, get_db
from .models import Image, InfrastructureAsset, Inspection, User
from .legacy_schemas import (
    AssetIn,
    AssetOut,
    AuthIn,
    InspectionIn,
    InspectionOut,
    PasswordIn,
    TokenOut,
    UserOut,
)
from app.routers import (
    assets_router,
    auth_router,
    images_router,
    inspections_router,
    users_router,
)


# ---------------- DATABASE AND APPLICATION ----------------

Base.metadata.create_all(bind=engine)
try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE infrastructure_assets ADD COLUMN custom_id VARCHAR(100)"))
except Exception:
    pass
try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE inspections ADD COLUMN notes VARCHAR(1000)"))
except Exception:
    pass

app = FastAPI(title="InfraScan API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:4173,"
        "http://127.0.0.1:5173,http://127.0.0.1:4173",
    ).split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- MOUNT ROUTERS ----------------

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(assets_router)
app.include_router(inspections_router)
app.include_router(images_router)

# Mount under /api prefix for frontend
app.include_router(users_router, prefix="/api")
app.include_router(inspections_router, prefix="/api")
app.include_router(images_router, prefix="/api")

MEDIA = Path(
    os.getenv(
        "INFRASCAN_MEDIA_DIR",
        Path(__file__).resolve().parent.parent / "media",
    )
)

MEDIA.mkdir(parents=True, exist_ok=True)

MAX_BYTES = 25 * 1024 * 1024
ALLOWED = {"image/jpeg", "image/png"}


# ---------------- YOLO CONFIGURATION ----------------

YOLO_MODEL_PATH = (
    Path(__file__).resolve().parents[2]
    / "runs"
    / "road_damage"
    / "yolo11n_initial"
    / "weights"
    / "best.pt"
)

_yolo_model = None
_yolo_model_lock = threading.Lock()
_yolo_annotated_paths: dict[int, Path] = {}


def get_yolo_model():
    global _yolo_model

    if _yolo_model is not None:
        return _yolo_model

    if YOLO is None:
        raise HTTPException(
            503,
            "Ultralytics YOLO is not installed",
        )

    if not YOLO_MODEL_PATH.is_file():
        raise HTTPException(
            503,
            f"YOLO model file not found: {YOLO_MODEL_PATH}",
        )

    with _yolo_model_lock:
        if _yolo_model is None:
            try:
                _yolo_model = YOLO(str(YOLO_MODEL_PATH))
            except Exception as exc:
                raise HTTPException(
                    503,
                    "Unable to load the YOLO model",
                ) from exc

    return _yolo_model


# ---------------- HEALTH CHECK ----------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "database": os.getenv(
            "DATABASE_URL",
            "sqlite:///./infrascan.db",
        ).split("://")[0],
    }


# ---------------- AUTHENTICATION ----------------

@app.post(
    "/api/auth/register",
    status_code=201,
)
def register(
    payload: AuthIn,
    db: Session = Depends(get_db),
):
    email = payload.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            409,
            "Email already registered",
        )

    full_name = payload.name or email.split("@")[0]
    user = User(
        full_name=full_name,
        email=email,
        password_hash=hash_password(payload.password),
        role="inspector",
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.email, "role": user.role, "user_id": user.user_id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "user_id": user.user_id,
        "id": user.user_id,
        "name": user.full_name,
        "full_name": user.full_name,
        "email": user.email,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "user": {
            "id": user.user_id,
            "user_id": user.user_id,
            "name": user.full_name,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
        },
    }


@app.post("/api/auth/login")
async def login(
    request: Request,
    db: Session = Depends(get_db),
):
    content_type = request.headers.get("content-type", "")
    username = None
    password = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            username = body.get("username") or body.get("email")
            password = body.get("password")
        except Exception:
            pass
    else:
        try:
            form = await request.form()
            username = form.get("username") or form.get("email")
            password = form.get("password")
        except Exception:
            pass

    if not username or not password:
        raise HTTPException(400, "Incorrect email or password")

    user = db.query(User).filter(User.email == str(username).lower().strip()).first()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            400,
            "Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            400,
            "Account is inactive",
        )

    token = create_access_token({"sub": user.email, "role": user.role, "user_id": user.user_id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "user_id": user.user_id,
        "id": user.user_id,
        "name": user.full_name,
        "full_name": user.full_name,
        "email": user.email,
        "is_active": user.is_active,
        "user": {
            "id": user.user_id,
            "user_id": user.user_id,
            "name": user.full_name,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
        },
    }


@app.get("/api/auth/profile", response_model=UserOut)
def profile(
    user: User = Depends(current_user),
):
    return user


@app.post("/api/auth/password", response_model=UserOut)
def change_password(
    payload: PasswordIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if not verify_password(
        payload.current_password,
        user.password_hash,
    ):
        raise HTTPException(
            400,
            "Current password is incorrect",
        )

    user.password_hash = hash_password(
        payload.new_password
    )

    db.commit()
    db.refresh(user)

    return user


# ---------------- INFRASTRUCTURE ASSETS ----------------

@app.get("/api/assets")
def list_assets(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    assets = db.query(InfrastructureAsset).order_by(
        InfrastructureAsset.created_at.desc()
    ).all()
    result = []
    for a in assets:
        result.append({
            "id": a.custom_id or a.asset_id,
            "asset_id": a.custom_id or a.asset_id,
            "name": a.name,
            "asset_type": a.asset_type,
            "type": a.asset_type,
            "material_type": a.material_type,
            "material": a.material_type,
            "address": a.address,
            "location": a.address,
            "latitude": a.latitude,
            "longitude": a.longitude,
            "construction_year": a.construction_year,
            "responsible_department": a.responsible_department,
            "department": a.responsible_department,
            "inspection_frequency_days": a.inspection_frequency_days,
            "inspection_frequency": f"{a.inspection_frequency_days} days",
            "importance_level": a.importance_level,
            "created_by": a.created_by,
            "created_at": a.created_at,
        })
    return result


@app.post(
    "/api/assets",
    status_code=201,
)
def create_asset(
    payload: AssetIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if payload.asset_id:
        existing = db.query(InfrastructureAsset).filter(
            InfrastructureAsset.custom_id == str(payload.asset_id)
        ).first()
        if existing:
            raise HTTPException(409, "Asset ID already exists")

    data = payload.sync_to_dict()
    asset = InfrastructureAsset(
        **data,
        created_by=user.user_id,
    )

    db.add(asset)
    db.commit()
    db.refresh(asset)

    return {
        "id": asset.custom_id or asset.asset_id,
        "asset_id": asset.custom_id or asset.asset_id,
        "name": asset.name,
        "asset_type": asset.asset_type,
        "type": asset.asset_type,
        "material_type": asset.material_type,
        "material": asset.material_type,
        "address": asset.address,
        "location": asset.address,
        "latitude": asset.latitude,
        "longitude": asset.longitude,
        "construction_year": asset.construction_year,
        "responsible_department": asset.responsible_department,
        "department": asset.responsible_department,
        "inspection_frequency_days": asset.inspection_frequency_days,
        "importance_level": asset.importance_level,
        "created_by": asset.created_by,
        "created_at": asset.created_at,
    }


@app.put(
    "/api/assets/{asset_id}",
)
def update_asset(
    asset_id: str,
    payload: AssetIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    query = db.query(InfrastructureAsset)
    if asset_id.isdigit():
        asset = query.filter(
            (InfrastructureAsset.asset_id == int(asset_id)) |
            (InfrastructureAsset.custom_id == asset_id)
        ).first()
    else:
        asset = query.filter(InfrastructureAsset.custom_id == asset_id).first()

    if not asset:
        raise HTTPException(
            404,
            "Asset not found",
        )

    data = payload.sync_to_dict()
    for key, value in data.items():
        setattr(asset, key, value)

    db.commit()
    db.refresh(asset)

    return {
        "id": asset.custom_id or asset.asset_id,
        "asset_id": asset.custom_id or asset.asset_id,
        "name": asset.name,
        "asset_type": asset.asset_type,
        "type": asset.asset_type,
        "material_type": asset.material_type,
        "material": asset.material_type,
        "address": asset.address,
        "location": asset.address,
        "latitude": asset.latitude,
        "longitude": asset.longitude,
        "construction_year": asset.construction_year,
        "responsible_department": asset.responsible_department,
        "department": asset.responsible_department,
        "inspection_frequency_days": asset.inspection_frequency_days,
        "importance_level": asset.importance_level,
        "created_by": asset.created_by,
        "created_at": asset.created_at,
    }


@app.delete(
    "/api/assets/{asset_id}",
    status_code=204,
)
def delete_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    query = db.query(InfrastructureAsset)
    if asset_id.isdigit():
        asset = query.filter(
            (InfrastructureAsset.asset_id == int(asset_id)) |
            (InfrastructureAsset.custom_id == asset_id)
        ).first()
    else:
        asset = query.filter(InfrastructureAsset.custom_id == asset_id).first()

    if not asset:
        raise HTTPException(
            404,
            "Asset not found",
        )

    db.delete(asset)
    db.commit()
    return None


# ---------------- INSPECTIONS ----------------

@app.post(
    "/api/inspections",
    response_model=InspectionOut,
    status_code=201,
)
def create_inspection(
    payload: InspectionIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if not db.get(
        InfrastructureAsset,
        payload.asset_id,
    ):
        raise HTTPException(
            404,
            "Asset not found",
        )

    if not db.get(User, payload.inspector_id):
        raise HTTPException(
            404,
            "Inspector not found",
        )

    inspection = Inspection(
        **payload.model_dump()
    )

    db.add(inspection)
    db.commit()
    db.refresh(inspection)

    return inspection


@app.get(
    "/api/inspections",
    response_model=list[InspectionOut],
)
def list_inspections(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return db.query(Inspection).order_by(
        Inspection.created_at.desc()
    ).all()


# ---------------- IMAGE VALIDATION ----------------

def read_validated(
    upload: UploadFile,
) -> tuple[bytes, PILImage.Image]:

    if upload.content_type not in ALLOWED:
        raise HTTPException(
            415,
            "Only JPG/JPEG and PNG images are supported",
        )

    raw = upload.file.read()

    if not raw:
        raise HTTPException(
            400,
            "Empty image file",
        )

    if len(raw) > MAX_BYTES:
        raise HTTPException(
            413,
            "Image exceeds 25 MB limit",
        )

    try:
        image = PILImage.open(
            io.BytesIO(raw)
        )

        image.load()

        image = ImageOps.exif_transpose(
            image
        ).convert("RGB")

    except Exception as exc:
        raise HTTPException(
            400,
            "Invalid image file",
        ) from exc

    if image.width < 227 or image.height < 227:
        raise HTTPException(
            422,
            "Image must be at least 227x227 pixels",
        )

    return raw, image


# ---------------- IMAGE STORAGE ----------------

def store_image(
    raw: bytes,
    image: PILImage.Image,
    filename: str,
    inspection_id: int,
    source: str,
    user: User,
    db: Session,
):
    safe_name = Path(
        filename or "upload.jpg"
    ).name

    key = f"{uuid.uuid4().hex}_{safe_name}"
    path = MEDIA / key

    gray = np.asarray(
        image.convert("L")
    )

    blur_score = float(
        cv2.Laplacian(
            gray,
            cv2.CV_64F,
        ).var()
    )

    brightness_score = float(
        np.mean(gray)
    )

    quality_status = "passed"
    notes = []

    if blur_score < 50:
        quality_status = "warning"
        notes.append("Image may be blurry")

    if brightness_score < 40 or brightness_score > 220:
        quality_status = "warning"
        notes.append(
            "Image lighting may affect assessment"
        )

    path.write_bytes(raw)

    record = Image(
        inspection_id=inspection_id,
        uploaded_by=user.user_id,
        file_path=str(path),
        original_filename=safe_name,
        file_hash=hashlib.sha256(raw).hexdigest(),
        width_px=image.width,
        height_px=image.height,
        file_size_bytes=len(raw),
        source=source,
        blur_score=blur_score,
        brightness_score=brightness_score,
        quality_status=quality_status,
        quality_notes="; ".join(notes) if notes else None,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return record


# ---------------- IMAGE METADATA ----------------

def image_metadata(record: Image):
    return {
        "image_id": record.image_id,
        "inspection_id": record.inspection_id,
        "uploaded_by": record.uploaded_by,
        "file_path": record.file_path,
        "original_filename": record.original_filename,
        "file_hash": record.file_hash,
        "width_px": record.width_px,
        "height_px": record.height_px,
        "file_size_bytes": record.file_size_bytes,
        "source": record.source,
        "blur_score": record.blur_score,
        "brightness_score": record.brightness_score,
        "quality_status": record.quality_status,
        "quality_notes": record.quality_notes,
        "gps_latitude": record.gps_latitude,
        "gps_longitude": record.gps_longitude,
        "captured_at": record.captured_at,
        "uploaded_at": record.uploaded_at,
        "processed_file_path": record.processed_file_path,
        "preprocess_status": record.preprocess_status,
        "preprocess_steps": record.preprocess_steps,
        "preprocessed_at": record.preprocessed_at,
    }


# ---------------- INSPECTION IMAGE UPLOAD ----------------

@app.post("/api/inspections/{inspection_id}/images")
def upload_inspection_images(
    inspection_id: int,
    files: list[UploadFile] = File(...),
    source: str = Form("phone"),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    inspection = db.get(
        Inspection,
        inspection_id,
    )

    if not inspection:
        raise HTTPException(
            404,
            "Inspection not found",
        )

    if source not in ["phone", "camera", "drone"]:
        raise HTTPException(
            422,
            "Source must be phone, camera, or drone",
        )

    results = []

    for upload in files:
        filename = upload.filename or "upload.jpg"

        try:
            raw, image = read_validated(upload)

            record = store_image(
                raw,
                image,
                filename,
                inspection_id,
                source,
                user,
                db,
            )

            result_status = (
                "warning"
                if record.quality_status == "warning"
                else "accepted"
            )

            results.append({
                "filename": filename,
                "status": result_status,
                "message": (
                    record.quality_notes
                    or "Image uploaded successfully"
                ),
                "image": image_metadata(record),
            })

        except HTTPException as exc:
            db.rollback()

            results.append({
                "filename": filename,
                "status": "rejected",
                "message": str(exc.detail),
                "image": None,
            })

        except Exception:
            db.rollback()

            results.append({
                "filename": filename,
                "status": "rejected",
                "message": "Unable to save image",
                "image": None,
            })

        finally:
            upload.file.close()

    return {
        "total_files": len(results),
        "accepted_count": sum(
            r["status"] == "accepted"
            for r in results
        ),
        "warning_count": sum(
            r["status"] == "warning"
            for r in results
        ),
        "rejected_count": sum(
            r["status"] == "rejected"
            for r in results
        ),
        "results": results,
    }


# ---------------- SINGLE IMAGE UPLOAD ----------------

@app.post("/api/images/upload")
def upload_image(
    file: UploadFile = File(...),
    inspection_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if inspection_id is None:
        raise HTTPException(
            422,
            "Inspection ID is required",
        )

    if not db.get(Inspection, inspection_id):
        raise HTTPException(
            404,
            "Inspection not found",
        )

    raw, image = read_validated(file)

    record = store_image(
        raw,
        image,
        file.filename or "upload.jpg",
        inspection_id,
        "phone",
        user,
        db,
    )

    return image_metadata(record)


# ---------------- IMAGE PREPROCESSING ----------------

@app.post("/api/images/{image_id}/preprocess")
def preprocess_image(
    image_id: int,
    resize: int = 1024,
    brightness: float = 1.0,
    contrast: float = 1.0,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    record = db.get(Image, image_id)

    if not record:
        raise HTTPException(
            404,
            "Image not found",
        )

    if resize < 227 or resize > 2048:
        raise HTTPException(
            422,
            "Resize must be between 227 and 2048",
        )

    try:
        image = PILImage.open(
            record.file_path
        ).convert("RGB")

        processed = ImageOps.fit(
            image,
            (resize, resize),
        )

        processed = ImageEnhance.Brightness(
            processed
        ).enhance(
            max(0.1, min(brightness, 3))
        )

        processed = ImageEnhance.Contrast(
            processed
        ).enhance(
            max(0.1, min(contrast, 3))
        )

        processed = processed.filter(
            ImageFilter.MedianFilter(size=3)
        ).filter(
            ImageFilter.SHARPEN
        )

        output_path = (
            MEDIA / f"processed_{record.image_id}.jpg"
        )

        processed.save(
            output_path,
            quality=90,
        )

        record.processed_file_path = str(output_path)
        record.preprocess_status = "done"

        record.preprocess_steps = json.dumps({
            "resize": [resize, resize],
            "brightness": brightness,
            "contrast": contrast,
            "noise_reduction": "median-3",
            "sharpening": "Pillow SHARPEN",
            "original_preserved": True,
        })

        record.preprocessed_at = datetime.now(
            timezone.utc
        )

        db.commit()

        return {
            "image_id": image_id,
            "processed_file_path": record.processed_file_path,
            "preprocess_status": record.preprocess_status,
            "preprocess_steps": json.loads(
                record.preprocess_steps
            ),
        }

    except Exception as exc:
        db.rollback()

        if isinstance(exc, HTTPException):
            raise

        raise HTTPException(
            500,
            "Image preprocessing failed",
        ) from exc


# ---------------- YOLO IMAGE ANALYSIS ----------------

@app.post("/api/images/{image_id}/analyze/yolo")
def analyze_yolo(
    image_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    record = db.get(Image, image_id)

    if not record:
        raise HTTPException(
            404,
            "Image not found",
        )

    image_path = Path(
        record.file_path
    ).resolve()

    try:
        image_path.relative_to(
            MEDIA.resolve()
        )

    except ValueError:
        raise HTTPException(
            400,
            "Image is outside the configured media directory",
        )

    if not image_path.is_file():
        raise HTTPException(
            404,
            "Uploaded image file not found",
        )

    model = get_yolo_model()

    try:
        predictions = model.predict(
            source=str(image_path),
            device="cpu",
            verbose=False,
        )

    except Exception as exc:
        raise HTTPException(
            500,
            "YOLO prediction failed",
        ) from exc

    if not predictions:
        raise HTTPException(
            500,
            "YOLO returned no prediction result",
        )

    prediction = predictions[0]
    names = prediction.names
    detections = []
    boxes = prediction.boxes

    if boxes is not None:
        coordinates = (
            boxes.xyxy.detach().cpu().numpy()
        )

        confidences = (
            boxes.conf.detach().cpu().numpy()
        )

        class_ids = (
            boxes.cls.detach().cpu().numpy().astype(int)
        )

        for box, confidence, class_id in zip(
            coordinates,
            confidences,
            class_ids,
        ):
            class_name = (
                names[class_id]
                if isinstance(names, (list, tuple))
                else names.get(class_id, str(class_id))
            )

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

    output_path = (
        MEDIA
        / f"yolo_{image_id}_{uuid.uuid4().hex}.jpg"
    )

    if not cv2.imwrite(
        str(output_path),
        np.asarray(prediction.plot()),
    ):
        raise HTTPException(
            500,
            "Unable to save annotated YOLO prediction image",
        )

    _yolo_annotated_paths[image_id] = output_path

    return {
        "image_id": image_id,
        "model": YOLO_MODEL_PATH.name,
        "total_detections": len(detections),
        "detections": detections,
        "annotated_image_url": (
            f"/api/images/{image_id}/analyze/yolo/annotated"
        ),
    }


# ---------------- ANNOTATED YOLO IMAGE ----------------

@app.get(
    "/api/images/{image_id}/analyze/yolo/annotated"
)
def get_annotated_yolo_image(
    image_id: int,
    user: User = Depends(current_user),
):
    output_path = _yolo_annotated_paths.get(
        image_id
    )

    if output_path is None or not output_path.is_file():
        raise HTTPException(
            404,
            "Annotated YOLO image not found; run analysis first",
        )

    try:
        output_path.resolve().relative_to(
            MEDIA.resolve()
        )

    except ValueError as exc:
        raise HTTPException(
            500,
            "Annotated image path is outside the media directory",
        ) from exc

    return FileResponse(
        output_path,
        media_type="image/jpeg",
    )
