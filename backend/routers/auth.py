from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from database import get_db
from models import User
from auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user
)

router = APIRouter(prefix="/api/auth", tags=["authentication"])

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    full_name: Optional[str] = None
    # If the client passes 'role' or 'status', it will be strictly ignored by the endpoint

class UserLoginRequest(BaseModel):
    username: str
    password: str

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = Field(None, min_length=6)

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    role: str
    status: str
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(req: UserRegisterRequest, db: Session = Depends(get_db)):
    # Check username uniqueness
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username is already registered")

    # Check email uniqueness
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email address is already registered")

    # Security rule: Public registration ALWAYS assigns role='user' and status='active'
    new_user = User(
        username=req.username.strip(),
        email=req.email.lower().strip(),
        hashed_password=get_password_hash(req.password),
        full_name=req.full_name.strip() if req.full_name else req.username,
        role="user",
        status="active",
        created_at=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=TokenResponse)
async def login_user(request: Request, db: Session = Depends(get_db)):
    # Support both JSON payload and OAuth2 form-data
    username = None
    password = None

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        username = body.get("username")
        password = body.get("password")
    else:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required"
        )

    # Allow login by username or email
    user = db.query(User).filter(
        (User.username == username) | (User.email == username.lower())
    ).first()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact an administrator."
        )

    # Record last login
    user.last_login = datetime.utcnow()
    db.commit()

    token = create_access_token(data={"sub": user.username, "role": user.role, "id": user.id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/profile", response_model=UserResponse)
def update_my_profile(
    req: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Only allow updating profile details, never role or status
    if req.full_name is not None:
        current_user.full_name = req.full_name.strip()

    if req.email is not None and req.email.lower() != current_user.email:
        existing = db.query(User).filter(User.email == req.email.lower()).first()
        if existing and existing.id != current_user.id:
            raise HTTPException(status_code=400, detail="Email is already in use by another account")
        current_user.email = req.email.lower()

    if req.new_password:
        if not req.current_password or not verify_password(req.current_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Current password verification failed")
        current_user.hashed_password = get_password_hash(req.new_password)

    db.commit()
    db.refresh(current_user)
    return current_user
