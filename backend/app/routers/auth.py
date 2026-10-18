from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.role import Role
from app.schemas.user import (
    UserCreate,
    UserOut,
    Token,
    UserUpdate,
    UserPasswordChange,
    RoleOut,
)
from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_user
from app.services.audit import log_action

router = APIRouter(tags=["Auth"])


@router.get("/roles", response_model=list[RoleOut])
def list_roles(db: Session = Depends(get_db)):
    """List available system roles for registration/management."""
    return db.query(Role).all()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # Check if email is already taken
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )

    # Determine role
    if user_in.role_id:
        role = db.query(Role).filter(Role.id == user_in.role_id).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role specified."
            )
        role_id = role.id
    else:
        # Default role: Civil Engineer or Inspector if first user
        default_role = db.query(Role).filter(Role.name == "Civil Engineer").first()
        role_id = default_role.id if default_role else 1

    new_user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        password_hash=hash_password(user_in.password),
        role_id=role_id,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_action(db, action="register", entity="user", entity_id=str(new_user.id), user_id=new_user.id)
    return new_user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # form_data.username is used for email
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive."
        )

    role_name = user.role.name if user.role else ""
    token = create_access_token({"sub": str(user.id), "role": role_name})

    log_action(db, action="login", entity="user", entity_id=str(user.id), user_id=user.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserOut)
def update_me(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if user_update.email and user_update.email != current_user.email:
        existing = db.query(User).filter(User.email == user_update.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already in use."
            )
        current_user.email = user_update.email

    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name

    db.commit()
    db.refresh(current_user)
    log_action(db, action="update", entity="user", entity_id=str(current_user.id), user_id=current_user.id)
    return current_user


@router.post("/change-password")
def change_password(
    pwd_in: UserPasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not verify_password(pwd_in.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password"
        )
    current_user.password_hash = hash_password(pwd_in.new_password)
    db.commit()
    log_action(db, action="change_password", entity="user", entity_id=str(current_user.id), user_id=current_user.id)
    return {"message": "Password changed successfully"}


@router.get("/oauth/google")
def oauth_google_stub():
    """Stub endpoint for Google OAuth2."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Google OAuth2 login is not implemented in Milestone 1. Planned for Milestone 2."
    )
