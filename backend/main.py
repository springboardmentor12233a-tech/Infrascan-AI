
from pathlib import Path
from io import BytesIO
from uuid import uuid4
import os
import base64

import cv2
import jwt
import numpy as np
import torch
import torch.nn as nn

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
from torchvision import transforms

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
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
password_hash = PasswordHash.recommended()

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
        raise HTTPException(
            status_code=400,
            detail="The file is empty.",
        )

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
        raise HTTPException(
            status_code=400,
            detail="Invalid image.",
        )

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

MODEL_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "crack_classifier.pth"
)

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


model = None
model_classes = []

image_transform = transforms.Compose([
    transforms.Resize((64, 64)),
    transforms.ToTensor(),
])

if MODEL_PATH.exists():
    checkpoint = torch.load(
        MODEL_PATH,
        map_location=MODEL_DEVICE,
        weights_only=True,
    )

    model_classes = checkpoint["classes"]
    model = CrackCNN(len(model_classes))
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()


# ---------------- Milestone 3 Six-Class CNN ----------------

M3_MODEL_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "m3_six_class_cnn.pth"
)


class SixClassCNN(nn.Module):
    def __init__(self, num_classes):
        super().__init__()

        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),

            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),

            nn.Conv2d(64, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),

            nn.AdaptiveAvgPool2d((1, 1)),
        )

        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.3),
            nn.Linear(128, num_classes),
        )

    def forward(self, x):
        return self.classifier(self.features(x))


m3_checkpoint = torch.load(
    M3_MODEL_PATH,
    map_location="cpu",
    weights_only=True,
)

m3_classes = m3_checkpoint["classes"]
m3_image_size = m3_checkpoint["image_size"]

m3_model = SixClassCNN(len(m3_classes))
m3_model.load_state_dict(m3_checkpoint["model_state_dict"])
m3_model.eval()

m3_transform = transforms.Compose([
    transforms.Resize((m3_image_size, m3_image_size)),
    transforms.ToTensor(),
])


# ---------------- Milestone 3 CNN Prediction API ----------------

@app.post("/predict-m3")
async def predict_m3(
    file: UploadFile = File(...),
    asset_id: int | None = None,
    current_user: dict = Depends(get_current_user),
):
    content, _, _ = await read_valid_image(file)

    image = Image.open(BytesIO(content)).convert("RGB")
    tensor = m3_transform(image).unsqueeze(0)

    with torch.no_grad():
        probabilities = torch.softmax(
            m3_model(tensor), dim=1
        )[0]

    index = int(probabilities.argmax().item())

    prediction = m3_classes[index]
    confidence = round(
        float(probabilities[index]) * 100, 2
    )

    db = SessionLocal()

    try:
        if asset_id is not None:
            asset = db.query(InfrastructureAsset).filter(
                InfrastructureAsset.id == asset_id
            ).first()

            if not asset:
                raise HTTPException(
                    status_code=404,
                    detail="Asset not found",
                )

        result = AssessmentResult(
            image_name=file.filename or "uploaded_image",
            prediction=prediction,
            confidence=confidence,
            asset_id=asset_id,
            model_name="Milestone 3 Six-Class CNN",
        )

        db.add(result)
        db.commit()
        db.refresh(result)

        result_id = result.id

    finally:
        db.close()

    return {
        "result_id": result_id,
        "model": "Milestone 3 Six-Class CNN",
        "prediction": prediction,
        "confidence_percent": confidence,
        "classes": m3_classes,
        "image_size": m3_image_size,
        "note": (
            "Experimental model; not validated "
            "for real-world safety decisions."
        ),
    }

# ---------------- Milestone 3 Vision Transformer ----------------

class PatchEmbedding(nn.Module):
    def __init__(self, image_size, patch_size, embed_dim):
        super().__init__()

        self.projection = nn.Conv2d(
            3,
            embed_dim,
            kernel_size=patch_size,
            stride=patch_size,
        )

        num_patches = (image_size // patch_size) ** 2

        self.class_token = nn.Parameter(
            torch.zeros(1, 1, embed_dim)
        )

        self.position_embedding = nn.Parameter(
            torch.zeros(1, num_patches + 1, embed_dim)
        )

    def forward(self, images):
        patches = self.projection(images)
        patches = patches.flatten(2).transpose(1, 2)

        class_tokens = self.class_token.expand(
            images.shape[0], -1, -1
        )

        tokens = torch.cat((class_tokens, patches), dim=1)

        return tokens + self.position_embedding


class TransformerBlock(nn.Module):
    def __init__(self, embed_dim, num_heads, mlp_ratio=2):
        super().__init__()

        self.norm1 = nn.LayerNorm(embed_dim)

        self.attention = nn.MultiheadAttention(
            embed_dim,
            num_heads,
            batch_first=True,
        )

        self.norm2 = nn.LayerNorm(embed_dim)

        self.mlp = nn.Sequential(
            nn.Linear(embed_dim, embed_dim * mlp_ratio),
            nn.GELU(),
            nn.Linear(embed_dim * mlp_ratio, embed_dim),
        )

    def forward(self, x):
        normalized = self.norm1(x)

        attended, _ = self.attention(
            normalized,
            normalized,
            normalized,
            need_weights=False,
        )

        x = x + attended
        x = x + self.mlp(self.norm2(x))

        return x


class SmallVisionTransformer(nn.Module):
    def __init__(self, num_classes, image_size, patch_size):
        super().__init__()

        self.patch_embedding = PatchEmbedding(
            image_size,
            patch_size,
            embed_dim=128,
        )

        self.blocks = nn.Sequential(*[
            TransformerBlock(128, num_heads=4)
            for _ in range(4)
        ])

        self.norm = nn.LayerNorm(128)
        self.head = nn.Linear(128, num_classes)

    def forward(self, images):
        x = self.patch_embedding(images)
        x = self.blocks(x)
        x = self.norm(x[:, 0])
        return self.head(x)


# Load saved Vision Transformer checkpoint

VIT_MODEL_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "m3_vit_small.pth"
)

vit_checkpoint = torch.load(
    VIT_MODEL_PATH,
    map_location="cpu",
    weights_only=True,
)

vit_classes = vit_checkpoint["class_names"]
vit_image_size = vit_checkpoint["image_size"]
vit_patch_size = vit_checkpoint["patch_size"]

vit_model = SmallVisionTransformer(
    len(vit_classes),
    vit_image_size,
    vit_patch_size,
)

vit_model.load_state_dict(
    vit_checkpoint["model_state_dict"]
)

vit_model.eval()

vit_transform = transforms.Compose([
    transforms.Resize((vit_image_size, vit_image_size)),
    transforms.ToTensor(),
    transforms.Normalize(
        (0.485, 0.456, 0.406),
        (0.229, 0.224, 0.225),
    ),
])


# ---------------- Milestone 3 ViT Prediction API ----------------

@app.post("/predict-vit")
async def predict_vit(
    file: UploadFile = File(...),
    asset_id: int | None = None,
    current_user: dict = Depends(get_current_user),
):
    content, _, _ = await read_valid_image(file)

    image = Image.open(
        BytesIO(content)
    ).convert("RGB")

    tensor = vit_transform(image).unsqueeze(0)

    with torch.no_grad():
        probabilities = torch.softmax(
            vit_model(tensor), dim=1
        )[0]

    index = int(probabilities.argmax().item())

    prediction = vit_classes[index]
    confidence = round(
        float(probabilities[index]) * 100, 2
    )

    db = SessionLocal()

    try:
        if asset_id is not None:
            asset = db.query(InfrastructureAsset).filter(
                InfrastructureAsset.id == asset_id
            ).first()

            if not asset:
                raise HTTPException(
                    status_code=404,
                    detail="Asset not found",
                )

        result = AssessmentResult(
            image_name=file.filename or "uploaded_image",
            prediction=prediction,
            confidence=confidence,
            asset_id=asset_id,
            model_name="Milestone 3 Vision Transformer",
        )

        db.add(result)
        db.commit()
        db.refresh(result)

        result_id = result.id

    finally:
        db.close()

    return {
        "result_id": result_id,
        "model": "Milestone 3 Vision Transformer",
        "prediction": prediction,
        "confidence_percent": confidence,
        "classes": vit_classes,
        "image_size": vit_image_size,
        "patch_size": vit_patch_size,
        "note": (
            "Experimental model; not validated "
            "for real-world safety decisions."
        ),
    }


# ---------------- Milestone 3 U-Net Segmentation ----------------

class UNetBlock(nn.Sequential):
    def __init__(self, in_channels, out_channels):
        super().__init__(
            nn.Conv2d(in_channels, out_channels, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, padding=1),
            nn.ReLU(inplace=True),
        )


class M3UNet(nn.Module):
    def __init__(self):
        super().__init__()

        self.enc1 = UNetBlock(3, 16)
        self.enc2 = UNetBlock(16, 32)
        self.enc3 = UNetBlock(32, 64)

        self.pool = nn.MaxPool2d(2)

        self.bottleneck = UNetBlock(64, 128)

        self.up3 = nn.ConvTranspose2d(
            128, 64, 2, stride=2
        )
        self.dec3 = UNetBlock(128, 64)

        self.up2 = nn.ConvTranspose2d(
            64, 32, 2, stride=2
        )
        self.dec2 = UNetBlock(64, 32)

        self.up1 = nn.ConvTranspose2d(
            32, 16, 2, stride=2
        )
        self.dec1 = UNetBlock(32, 16)

        self.output = nn.Conv2d(16, 1, 1)

    def forward(self, x):
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))

        b = self.bottleneck(self.pool(e3))

        d3 = self.dec3(
            torch.cat([self.up3(b), e3], dim=1)
        )

        d2 = self.dec2(
            torch.cat([self.up2(d3), e2], dim=1)
        )

        d1 = self.dec1(
            torch.cat([self.up1(d2), e1], dim=1)
        )

        return self.output(d1)


UNET_MODEL_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "unet_crack_improved.pth"
)

unet_model = M3UNet()

unet_model.load_state_dict(
    torch.load(
        UNET_MODEL_PATH,
        map_location="cpu",
        weights_only=True,
    )
)

unet_model.eval()


@app.post("/predict-unet")
async def predict_unet(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    content, _, _ = await read_valid_image(file)

    image = Image.open(
        BytesIO(content)
    ).convert("RGB")

    image = image.resize((256, 256))

    image_array = np.asarray(
        image,
        dtype=np.float32,
    ) / 255.0

    image_array = np.transpose(
        image_array,
        (2, 0, 1),
    ).copy()

    tensor = torch.from_numpy(
        image_array
    ).unsqueeze(0)

    with torch.no_grad():
        probability_map = torch.sigmoid(
            unet_model(tensor)
        )

        mask = (
            (probability_map >= 0.5)
            .squeeze()
            .numpy()
            .astype(np.uint8)
            * 255
        )

    success, encoded_mask = cv2.imencode(
        ".png",
        mask,
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Could not generate segmentation mask.",
        )

    mask_base64 = base64.b64encode(
        encoded_mask.tobytes()
    ).decode("utf-8")

    return {
        "model": "Milestone 3 U-Net",
        "image_size": 256,
        "threshold": 0.5,
        "crack_pixels": int(np.count_nonzero(mask)),
        "crack_pixel_percentage": round(
            float(np.count_nonzero(mask)) / mask.size * 100,
            2,
        ),
        "mask_base64": mask_base64,
        "note": (
            "Experimental segmentation; not validated "
            "for real-world safety decisions."
        ),
    }

# ---------------- Legacy Crack Prediction API ----------------

@app.post("/predict-crack")
async def predict_crack(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="Trained model not found. Train the model first.",
        )

    content, _, _ = await read_valid_image(file)

    try:
        image = Image.open(
            BytesIO(content)
        ).convert("RGB")

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid image file.",
        )

    tensor = image_transform(image).unsqueeze(0)

    with torch.no_grad():
        probabilities = torch.softmax(
            model(tensor), dim=1
        )[0]

    predicted_index = int(
        probabilities.argmax().item()
    )

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
        db.refresh(result)

        result_id = result.id

    finally:
        db.close()

    return {
        "result_id": result_id,
        "prediction": predicted_class,
        "confidence_percent": confidence,
        "classes": model_classes,
        "note": (
            "Experimental prototype trained on a small sample "
            "of Deck images. Not validated for real-world "
            "infrastructure safety decisions."
        ),
    }


# ---------------- Infrastructure Assets ----------------

class AssetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    asset_type: str = Field(min_length=1, max_length=50)
    location: str = Field(min_length=1, max_length=200)
    latitude: float | None = None
    longitude: float | None = None


@app.get("/assets")
def get_assets(
    current_user: dict = Depends(get_current_user),
):
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
                "latitude": asset.latitude,
                "longitude": asset.longitude,
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
        if (asset.latitude is None) != (asset.longitude is None):
            raise HTTPException(
                status_code=400,
                detail="Both latitude and longitude are required together.",
            )

        if asset.latitude is not None:
            if not -90 <= asset.latitude <= 90:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid latitude.",
                )

            if not -180 <= asset.longitude <= 180:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid longitude.",
                )

        new_asset = InfrastructureAsset(
            name=asset.name.strip(),
            asset_type=asset.asset_type.strip(),
            location=asset.location.strip(),
            latitude=asset.latitude,
            longitude=asset.longitude,
        )

        db.add(new_asset)
        db.commit()
        db.refresh(new_asset)

        return {
            "id": new_asset.id,
            "name": new_asset.name,
            "type": new_asset.asset_type,
            "location": new_asset.location,
            "latitude": new_asset.latitude,
            "longitude": new_asset.longitude,
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

        return {
            "message": "Registration successful"
        }

    finally:
        db.close()


@app.post("/auth/login")
def login(data: LoginRequest):
    db = SessionLocal()

    try:
        email = str(data.email).lower()

        user = (
            db.query(User)
            .filter(User.email == email)
            .first()
        )

        if not user or not password_hash.verify(
            data.password,
            user.hashed_password,
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password",
            )

        token = jwt.encode(
            {
                "sub": str(user.id),
                "role": "inspector",
            },
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


# ---------------- Assessment History ----------------

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


# ---------------- Milestone 3 Dashboard APIs ----------------

@app.get("/assets/{asset_id}/history")
def get_asset_history(
    asset_id: int,
    current_user: dict = Depends(get_current_user),
):
    db = SessionLocal()

    try:
        asset = (
            db.query(InfrastructureAsset)
            .filter(InfrastructureAsset.id == asset_id)
            .first()
        )

        if not asset:
            raise HTTPException(
                status_code=404,
                detail="Asset not found",
            )

        results = (
            db.query(AssessmentResult)
            .filter(AssessmentResult.asset_id == asset_id)
            .order_by(AssessmentResult.id.desc())
            .all()
        )

        return {
            "asset_id": asset.id,
            "asset_name": asset.name,
            "history": [
                {
                    "id": item.id,
                    "image_name": item.image_name,
                    "prediction": item.prediction,
                    "confidence": item.confidence,
                    "model_name": item.model_name,
                    "severity": item.severity,
                    "maintenance_priority": item.maintenance_priority,
                    "created_at": (
                        item.created_at.isoformat()
                        if item.created_at
                        else None
                    ),
                }
                for item in results
            ],
        }

    finally:
        db.close()


@app.get("/maintenance-priorities")
def get_maintenance_priorities(
    current_user: dict = Depends(get_current_user),
):
    db = SessionLocal()

    try:
        results = (
            db.query(AssessmentResult)
            .filter(
                (AssessmentResult.severity.isnot(None))
                | (
                    AssessmentResult.maintenance_priority.isnot(None)
                )
            )
            .order_by(AssessmentResult.id.desc())
            .all()
        )

        return {
            "priorities": [
                {
                    "id": item.id,
                    "image_name": item.image_name,
                    "prediction": item.prediction,
                    "confidence": item.confidence,
                    "severity": item.severity,
                    "maintenance_priority": item.maintenance_priority,
                    "created_at": (
                        item.created_at.isoformat()
                        if item.created_at
                        else None
                    ),
                }
                for item in results
            ]
        }

    finally:
        db.close()
