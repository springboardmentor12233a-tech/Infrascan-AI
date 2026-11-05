from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from backend.services.auth import decode_access_token
from backend.services.auth import (
    hash_password,
    verify_password,
    create_access_token
)
import sqlite3
from pydantic import BaseModel
from backend.database import get_connection
from backend.services.image_preprocessing import preprocess_image
from fastapi import FastAPI, UploadFile, File, HTTPException
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from io import BytesIO
import uuid
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(
    title="InfraScan API",
    description="AI-Powered Crack and Damage Assessment for Civil Infrastructure",
    version="1.0.0"
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    return decode_access_token(token)

def require_role(required_role):
    def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") != required_role:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker
class Asset(BaseModel):
    name: str
    infrastructure_type: str
    location: str = ""
    description: str = ""
class UserRegister(BaseModel):
    name: str
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Upload directory
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@app.get("/")
def home():
    return {
        "project": "InfraScan",
        "message": "InfraScan backend is running successfully!",
        "status": "online"
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "InfraScan API"
    }


@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):

    # Check file extension
    allowed_extensions = {".jpg", ".jpeg", ".png"}
    extension = Path(file.filename or "").suffix.lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, JPEG and PNG images are allowed."
        )

    # Read file with size limit
    contents = await file.read(MAX_FILE_SIZE + 1)
    await file.close()

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Image size must not exceed 10 MB."
        )

    # Verify actual image content
    try:
        image = Image.open(BytesIO(contents))
        image.verify()

        if image.format not in {"JPEG", "PNG"}:
            raise HTTPException(
                status_code=400,
                detail="Invalid image format."
            )

    except (UnidentifiedImageError, OSError):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is not a valid image."
        )

    # Generate unique filename
    unique_filename = f"{uuid.uuid4().hex}{extension}"
    file_path = UPLOAD_DIR / unique_filename

    # Save image
    file_path.write_bytes(contents)
    preprocessing_result = preprocess_image(file_path)

    return {
        "message": "Image uploaded successfully!",
        "filename": unique_filename,
        "size_bytes": len(contents),
        "status": "success",
        "preprocessing": preprocessing_result
    }
@app.post("/api/assets")
def create_asset(asset: Asset, current_user: dict = Depends(require_role("admin"))):    
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO assets (name, infrastructure_type, location, description)
        VALUES (?, ?, ?, ?)
    """, (
        asset.name,
        asset.infrastructure_type,
        asset.location,
        asset.description
    ))

    asset_id = cursor.lastrowid
    connection.commit()
    connection.close()

    return {
        "message": "Infrastructure asset added successfully!",
        "asset_id": asset_id,
        "status": "success"
    }


@app.get("/api/assets")
def get_assets():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM assets")
    assets = [dict(row) for row in cursor.fetchall()]

    connection.close()

    return {
        "assets": assets,
        "total": len(assets)
    }
@app.post("/api/register")
def register_user(user: UserRegister):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT id FROM users WHERE email = ?",
        (user.email,)
    )

    if cursor.fetchone():
        connection.close()
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    hashed_password = hash_password(user.password)

    cursor.execute("""
        INSERT INTO users (name, email, password, role)
        VALUES (?, ?, ?, ?)
    """, (user.name, user.email, hashed_password, "inspector"))

    connection.commit()
    user_id = cursor.lastrowid
    connection.close()

    return {
        "message": "User registered successfully",
        "user_id": user_id
    }


@app.post("/api/login")
def login_user(user: UserLogin):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email = ?",
        (user.email,)
    )

    existing_user = cursor.fetchone()
    connection.close()

    if not existing_user or not verify_password(
        user.password, existing_user["password"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    token = create_access_token(
        existing_user["id"],
        existing_user["role"]
    )

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "role": existing_user["role"]
    }