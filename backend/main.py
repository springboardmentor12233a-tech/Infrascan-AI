from pathlib import Path
from io import BytesIO
from uuid import uuid4
import os

import cv2
import jwt
import numpy as np
from PIL import Image
from pwdlib import PasswordHash
from pydantic import BaseModel, EmailStr, Field

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Depends,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
try:
    import torch
    import torch.nn as nn
    from torchvision import transforms
except (ImportError, OSError) as exc:
    torch = None
    nn = None
    transforms = None
    print(f"AI model unavailable: {exc}")

from database import (
    SessionLocal,
    InfrastructureAsset,
    AssessmentResult,
    User,
)

# ---------------- Configuration ----------------

app = FastAPI(
    title="InfraScan API",
    description="Infrastructure Crack and Damage Assessment Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

password_hash = PasswordHash.recommended()

# Set INFRASCAN_SECRET_KEY in your environment before deployment.
SECRET_KEY = os.getenv(
    "INFRASCAN_SECRET_KEY",
    "development-only-change-this-secret-key",
)
ALGORITHM = "HS256"
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        user_id = payload.get("sub")
        role = payload.get("role")

        if not user_id or not role:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token",
            )

        return {
            "user_id": user_id,
            "role": role,
        }

    except jwt.PyJWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token",
        )

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024


# ---------------- Basic endpoints ----------------

@app.get("/")
def home():
    return {
        "message": "Welcome to InfraScan API",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# ---------------- Image upload ----------------

async def read_valid_image(file: UploadFile):
    extension = Path(file.filename or "").suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, JPEG, PNG and WEBP images are allowed.",
        )

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="The file is empty.")

    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="Image size must be 10 MB or less.",
        )

    try:
        with Image.open(BytesIO(content)) as check_image:
            check_image.verify()

        with Image.open(BytesIO(content)) as image:
            image_details = {
                "width": image.width,
                "height": image.height,
                "format": image.format,
                "mode": image.mode,
            }
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid or corrupted image file.",
        )

    return content, extension, image_details


@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    content, extension, image_details = await read_valid_image(file)

    image_name = f"{uuid4().hex}{extension}"
    image_path = UPLOAD_DIR / image_name
    image_path.write_bytes(content)

    return {
        "message": "Image uploaded successfully",
        "filename": image_name,
        "size_bytes": len(content),
        "image_details": image_details,
    }


# ---------------- Basic image preprocessing ----------------

@app.post("/detect-cracks")
async def detect_cracks(file: UploadFile = File(...)):
    content, _, image_details = await read_valid_image(file)

    image_array = np.frombuffer(content, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        raise HTTPException(status_code=400, detail="Invalid image.")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    return {
        "message": "Basic image processing completed",
        "method": "Grayscale, Gaussian blur and Canny edge detection",
        "image_width": int(image.shape[1]),
        "image_height": int(image.shape[0]),
        "edge_pixels": int(np.count_nonzero(edges)),
        "image_details": image_details,
        "note": (
            "Detected edges are not confirmed cracks. "
            "This preprocessing result is not a safety assessment."
        ),
    }


# ---------------- CNN model ----------------


# ---------------- CNN model ----------------

MODEL_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "crack_classifier.pth"
)

model = None
model_classes = []
image_transform = None

if torch is not None and nn is not None and transforms is not None:
    MODEL_DEVICE = torch.device("cpu")

    class CrackCNN(nn.Module):
        def __init__(self, num_classes):
            super().__init__()
            self.features = nn.Sequential(
                nn.Conv2d(3, 16, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.MaxPool2d(2),
                nn.Conv2d(16, 32, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.MaxPool2d(2),
                nn.Conv2d(32, 64, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.AdaptiveAvgPool2d((1, 1)),
            )
            self.classifier = nn.Linear(64, num_classes)

        def forward(self, x):
            return self.classifier(self.features(x).flatten(1))

    image_transform = transforms.Compose([
        transforms.Resize((64, 64)),
        transforms.ToTensor(),
    ])

    if MODEL_PATH.exists():
        try:
            checkpoint = torch.load(
                MODEL_PATH,
                map_location=MODEL_DEVICE,
                weights_only=True,
            )
            model_classes = checkpoint["classes"]
            model = CrackCNN(len(model_classes))
            model.load_state_dict(checkpoint["model_state_dict"])
            model.eval()
            print("AI model loaded successfully.")
        except Exception as exc:
            print(f"AI model unavailable: {exc}")
            model = None
            model_classes = []
    else:
        print(f"AI model file not found: {MODEL_PATH}")
else:
    print("PyTorch unavailable. AI prediction is disabled.")


# ---------------- Crack prediction ----------------

@app.post("/predict-crack")
async def predict_crack(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    if model is None or image_transform is None or torch is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "AI model is unavailable because PyTorch could not load "
                "the model. "
            ),
        )

    content, _, _ = await read_valid_image(file)

    try:
        image = Image.open(BytesIO(content)).convert("RGB")
        tensor = image_transform(image).unsqueeze(0)

        with torch.no_grad():
            probabilities = torch.softmax(model(tensor), dim=1)[0]

        predicted_index = int(probabilities.argmax().item())
        predicted_class = model_classes[predicted_index]
        confidence = round(
            float(probabilities[predicted_index].item()) * 100,
            2,
        )

        db = SessionLocal()
        try:
            result = AssessmentResult(
                image_name=file.filename or "uploaded_image",
                prediction=predicted_class,
                confidence=confidence,
            )
            db.add(result)
            db.commit()
        finally:
            db.close()

        return {
            "prediction": predicted_class,
            "confidence_percent": confidence,
            "classes": model_classes,
            "note": (
                "Experimental prototype; not validated for "
                "real-world infrastructure safety decisions."
            ),
        }

    except HTTPException:
        raise
    except Exception as exc:
        print(f"Prediction error: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Prediction failed. Check the backend terminal.",
        )


# ---------------- Infrastructure assets ----------------

class AssetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    asset_type: str = Field(min_length=1, max_length=50)
    location: str = Field(min_length=1, max_length=200)


@app.get("/assets")
def get_assets(current_user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        assets = (
            db.query(InfrastructureAsset)
            .order_by(InfrastructureAsset.id.desc())
            .all()
        )
        return [
            {
                "id": asset.id,
                "name": asset.name,
                "type": asset.asset_type,
                "location": asset.location,
            }
            for asset in assets
        ]
    finally:
        db.close()

@app.post("/assets")
def create_asset(
    asset: AssetCreate,
    current_user: dict = Depends(get_current_user),
):
    db = SessionLocal()
    try:
        new_asset = InfrastructureAsset(
            name=asset.name.strip(),
            asset_type=asset.asset_type.strip(),
            location=asset.location.strip(),
        )
        db.add(new_asset)
        db.commit()
        db.refresh(new_asset)

        return {
            "id": new_asset.id,
            "name": new_asset.name,
            "type": new_asset.asset_type,
            "location": new_asset.location,
        }
    finally:
        db.close()


# ---------------- Authentication ----------------

class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


@app.post("/auth/register")
def register(data: RegisterRequest):
    db = SessionLocal()
    try:
        email = str(data.email).lower()
        existing_user = (
            db.query(User)
            .filter(User.email == email)
            .first()
        )

        if existing_user:
            raise HTTPException(
                status_code=409,
                detail="Email already registered",
            )

        user = User(
            name=data.name.strip(),
            email=email,
            hashed_password=password_hash.hash(data.password),
        )
        db.add(user)
        db.commit()

        return {"message": "Registration successful"}
    finally:
        db.close()


@app.post("/auth/login")
def login(data: LoginRequest):
    db = SessionLocal()
    try:
        email = str(data.email).lower()
        user = db.query(User).filter(User.email == email).first()

        if not user or not password_hash.verify(
            data.password,
            user.hashed_password,
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password",
            )

        token = jwt.encode(
            {"sub": str(user.id), "role": "inspector"},
            SECRET_KEY,
            algorithm=ALGORITHM,
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "name": user.name,
        }
    finally:
        db.close()


# ---------------- Assessment history ----------------

@app.get("/assessment-results")
def get_assessment_results():
    db = SessionLocal()
    try:
        results = (
            db.query(AssessmentResult)
            .order_by(AssessmentResult.id.desc())
            .all()
        )
        return [
            {
                "id": result.id,
                "image_name": result.image_name,
                "prediction": result.prediction,
                "confidence": result.confidence,
                "created_at": (
                    result.created_at.isoformat()
                    if result.created_at
                    else None
                ),
            }
            for result in results
        ]
    finally:
        db.close()