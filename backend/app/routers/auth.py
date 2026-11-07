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
    email = user_data.email.lower().strip()
    existing_user = db.query(User).filter(User.email == email).first()
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
        email=email,
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

    token = create_access_token({"sub": new_user.email, "role": new_user.role, "user_id": new_user.user_id})
    res = UserResponse.model_validate(new_user)
    res.access_token = token
    return res


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    db: Session = Depends(get_db),
):
    """Authenticate with OAuth2 password form or JSON and return JWT token and role."""
    client_ip = request.client.host if request.client else None
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

    invalid_credentials_error = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Incorrect email or password",
    )

    if not username or not password:
        raise invalid_credentials_error

    # Look up user by email
    user = db.query(User).filter(User.email == str(username).lower().strip()).first()

    if not user or not verify_password(password, user.password_hash):
        create_audit_log(
            db=db,
            action="login_failure",
            user_id=user.user_id if user else None,
            entity_type="auth",
            entity_id=str(username),
            ip_address=client_ip,
        )
        raise invalid_credentials_error

    if not user.is_active:
        create_audit_log(
            db=db,
            action="login_failure",
            user_id=user.user_id,
            entity_type="auth",
            entity_id=str(username),
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

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
    )
