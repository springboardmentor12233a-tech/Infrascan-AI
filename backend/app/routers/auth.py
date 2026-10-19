from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import TokenResponse, UserRegisterRequest, UserResponse
from app.services.audit import create_audit_log
from app.services.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserRegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Register a new user. Role is automatically set to inspector."""
    # Check if email is already taken
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered",
        )

    # Hash password using bcrypt directly
    hashed = hash_password(user_data.password)

    # New users always receive the inspector role
    new_user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        password_hash=hashed,
        role="inspector",
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Record audit log
    client_ip = request.client.host if request.client else None
    create_audit_log(
        db=db,
        action="register",
        user_id=new_user.user_id,
        entity_type="user",
        entity_id=str(new_user.user_id),
        ip_address=client_ip,
    )

    return new_user


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate with OAuth2 password form and return JWT token and role."""
    client_ip = request.client.host if request.client else None

    # Look up user by email
    user = db.query(User).filter(User.email == form_data.username).first()

    # Generic error message to prevent email enumeration
    invalid_credentials_error = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Incorrect email or password",
    )

    if not user or not verify_password(form_data.password, user.password_hash):
        create_audit_log(
            db=db,
            action="login_failure",
            user_id=user.user_id if user else None,
            entity_type="auth",
            entity_id=form_data.username,
            ip_address=client_ip,
        )
        raise invalid_credentials_error

    if not user.is_active:
        create_audit_log(
            db=db,
            action="login_failure",
            user_id=user.user_id,
            entity_type="auth",
            entity_id=form_data.username,
            ip_address=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is inactive",
        )

    # Generate 30-minute JWT token
    token = create_access_token({"sub": user.email, "role": user.role, "user_id": user.user_id})

    create_audit_log(
        db=db,
        action="login_success",
        user_id=user.user_id,
        entity_type="auth",
        entity_id=str(user.user_id),
        ip_address=client_ip,
    )

    return TokenResponse(access_token=token, token_type="bearer", role=user.role)
