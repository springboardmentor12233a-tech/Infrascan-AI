from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from database import get_db
from models import User, Inspection, InspectionResult, Asset
from auth import require_admin, get_password_hash
from routers.inspection import build_inspection_response

router = APIRouter(prefix="/api/admin", tags=["admin"])

class AdminUserView(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    status: str
    created_at: datetime
    last_login: Optional[datetime]
    inspection_count: int

    class Config:
        from_attributes = True

class StatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(active|inactive)$")

class CreateAdminRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    full_name: Optional[str] = None

@router.get("/overview")
def get_admin_overview(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.status == "active").count()
    inactive_users = total_users - active_users
    admin_count = db.query(User).filter(User.role == "admin").count()
    regular_users = total_users - admin_count

    total_inspections = db.query(Inspection).count()
    cracked_inspections = db.query(InspectionResult).filter(InspectionResult.crack_detected == True).count()
    critical_inspections = db.query(InspectionResult).filter(
        InspectionResult.severity_level.like("%Critical%") | InspectionResult.urgent_review_required == True
    ).count()

    # Recent inspections with inspector/user information
    recent_inspections_raw = db.query(Inspection).order_by(Inspection.timestamp.desc()).limit(8).all()
    recent_inspections = []
    for insp in recent_inspections_raw:
        recent_inspections.append({
            "id": insp.id,
            "asset_name": insp.asset.name if insp.asset else "Unassigned",
            "inspector_name": insp.inspector_name,
            "user_id": insp.user_id,
            "username": insp.user.username if insp.user else "Anonymous/Demo",
            "timestamp": insp.timestamp,
            "severity_level": insp.results.severity_level if insp.results else "N/A",
            "priority_level": insp.results.priority_level if insp.results else "N/A",
            "crack_detected": insp.results.crack_detected if insp.results else False
        })

    # Severity distribution
    sev_query = db.query(InspectionResult.severity_level, func.count(InspectionResult.id)).group_by(InspectionResult.severity_level).all()
    severity_distribution = {lvl: cnt for lvl, cnt in sev_query if lvl}

    # Priority distribution
    prio_query = db.query(InspectionResult.priority_level, func.count(InspectionResult.id)).group_by(InspectionResult.priority_level).all()
    priority_distribution = {lvl: cnt for lvl, cnt in prio_query if lvl}

    return {
        "user_statistics": {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": inactive_users,
            "admin_count": admin_count,
            "regular_users": regular_users
        },
        "inspection_statistics": {
            "total_inspections": total_inspections,
            "cracked_inspections": cracked_inspections,
            "critical_inspections": critical_inspections,
            "total_assets": db.query(Asset).count()
        },
        "severity_distribution": severity_distribution,
        "priority_distribution": priority_distribution,
        "recent_activity": recent_inspections
    }

@router.get("/users")
def list_users(
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(User)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter((User.username.like(s)) | (User.email.like(s)) | (User.full_name.like(s)))

    if role and role != "all":
        query = query.filter(User.role == role)

    if status and status != "all":
        query = query.filter(User.status == status)

    users = query.order_by(User.created_at.desc()).all()

    results = []
    for u in users:
        insp_count = db.query(Inspection).filter(Inspection.user_id == u.id).count()
        results.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "status": u.status,
            "created_at": u.created_at,
            "last_login": u.last_login,
            "inspection_count": insp_count
        })

    return results

@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    req: StatusUpdateRequest,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Guard: prevent admin from deactivating themselves if they are the only active admin
    if user.id == current_admin.id and req.status == "inactive":
        active_admins = db.query(User).filter(User.role == "admin", User.status == "active").count()
        if active_admins <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot deactivate the only active administrator account."
            )

    user.status = req.status
    db.commit()
    db.refresh(user)
    return {
        "message": f"User '{user.username}' status updated to '{user.status}' successfully.",
        "user_id": user.id,
        "status": user.status
    }

@router.post("/users/create-admin", status_code=status.HTTP_201_CREATED)
def create_admin_user(
    req: CreateAdminRequest,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username is already registered")

    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email is already registered")

    admin = User(
        username=req.username.strip(),
        email=req.email.lower().strip(),
        hashed_password=get_password_hash(req.password),
        full_name=req.full_name.strip() if req.full_name else f"Admin {req.username}",
        role="admin",
        status="active",
        created_at=datetime.utcnow()
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    return {
        "message": f"Administrator '{admin.username}' created successfully.",
        "user": {
            "id": admin.id,
            "username": admin.username,
            "email": admin.email,
            "full_name": admin.full_name,
            "role": admin.role,
            "status": admin.status
        }
    }

@router.get("/inspections")
def get_all_inspections_admin(
    user_id: Optional[int] = Query(None),
    severity: Optional[str] = Query(None),
    crack_only: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(Inspection)

    if user_id:
        query = query.filter(Inspection.user_id == user_id)

    if crack_only:
        query = query.join(InspectionResult).filter(InspectionResult.crack_detected == True)

    if severity and severity != "all":
        query = query.join(InspectionResult).filter(InspectionResult.severity_level.ilike(f"%{severity}%"))

    if search:
        s = f"%{search.strip()}%"
        query = query.outerjoin(Asset).filter(
            (Inspection.inspector_name.ilike(s)) |
            (Inspection.notes.ilike(s)) |
            (Asset.name.ilike(s))
        )

    inspections = query.order_by(Inspection.timestamp.desc()).all()

    formatted = []
    for insp in inspections:
        item = build_inspection_response(insp)
        item["user_id"] = insp.user_id
        item["user_username"] = insp.user.username if insp.user else "Unassigned / Pre-RBAC"
        formatted.append(item)

    return formatted

@router.get("/analytics")
def get_admin_system_analytics(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    # Real stored inspection trends (by month/date)
    inspections = db.query(Inspection.timestamp).all()
    timeline = {}
    for (ts,) in inspections:
        if ts:
            key = ts.strftime("%Y-%m")
            timeline[key] = timeline.get(key, 0) + 1

    # Severity distribution
    sev_query = db.query(InspectionResult.severity_level, func.count(InspectionResult.id)).group_by(InspectionResult.severity_level).all()
    severity_breakdown = {lvl: cnt for lvl, cnt in sev_query if lvl}

    # Priority distribution
    prio_query = db.query(InspectionResult.priority_level, func.count(InspectionResult.id)).group_by(InspectionResult.priority_level).all()
    priority_breakdown = {lvl: cnt for lvl, cnt in prio_query if lvl}

    # Active inspectors
    inspector_query = db.query(Inspection.inspector_name, func.count(Inspection.id)).group_by(Inspection.inspector_name).order_by(desc(func.count(Inspection.id))).limit(5).all()
    top_inspectors = [{"name": name, "count": cnt} for name, cnt in inspector_query if name]

    # Damage area distribution
    total_area_px = db.query(func.sum(InspectionResult.crack_area_px)).scalar() or 0
    avg_area_px = db.query(func.avg(InspectionResult.crack_area_px)).scalar() or 0

    return {
        "monthly_inspections": timeline,
        "severity_distribution": severity_breakdown,
        "priority_distribution": priority_breakdown,
        "top_inspectors": top_inspectors,
        "aggregate_metrics": {
            "total_crack_area_px": total_area_px,
            "average_crack_area_px": round(avg_area_px, 1),
            "total_inspections": len(inspections)
        }
    }
