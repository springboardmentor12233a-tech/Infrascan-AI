"""Router for damage map, geospatial features, hotspots, and inspector routing.

Endpoints:
- GET /map/assets: GeoJSON FeatureCollection of assets with current condition and filters.
- GET /map/damage: GeoJSON Point features for damage markers from EXIF GPS (fallback to asset).
- GET /map/hotspots: Weighted points / grid-aggregated heatmap cells.
- GET /map/summary: Region-wise summaries grouped by district (or asset type).
- GET /map/route: Ordered inspection stops (nearest-neighbour haversine) for an inspector on a date.
"""

from datetime import date, datetime
import math
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, select

from app.database import get_db
from app.deps import get_current_user
from app.models.asset import InfrastructureAsset
from app.models.image import Image
from app.models.inspection import Inspection
from app.models.severity import SeverityAssessment, InspectionSeverity
from app.models.analysis import Detection, AnalysisRun
from app.models.user import User

router = APIRouter(prefix="/map", tags=["Damage Map"])

SEVERITY_RANKS = {"none": 0, "minor": 1, "moderate": 2, "severe": 3, "critical": 4}
RANK_TO_SEVERITY = {0: "none", 1: "minor", 2: "moderate", 3: "severe", 4: "critical"}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate straight-line great circle distance between two points in km."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2.0) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def validate_bbox(
    min_lat: Optional[float],
    min_lon: Optional[float],
    max_lat: Optional[float],
    max_lon: Optional[float],
) -> None:
    """Validate bounding box coordinates."""
    coords = [min_lat, min_lon, max_lat, max_lon]
    if any(c is not None for c in coords):
        if any(c is None for c in coords):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All four bounding box coordinates (min_lat, min_lon, max_lat, max_lon) must be provided together.",
            )
        if not (-90.0 <= min_lat <= 90.0 and -90.0 <= max_lat <= 90.0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Latitude must be between -90 and 90 degrees.",
            )
        if not (-180.0 <= min_lon <= 180.0 and -180.0 <= max_lon <= 180.0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Longitude must be between -180 and 180 degrees.",
            )
        if min_lat > max_lat:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="min_lat cannot be greater than max_lat.",
            )
        if min_lon > max_lon:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="min_lon cannot be greater than max_lon.",
            )


def get_asset_current_condition(
    asset: InfrastructureAsset,
    db: Session,
    current_user: User,
) -> Dict[str, Any]:
    """
    Computes current condition of an asset per definition:
    Taken from the latest inspection that has at least one severity assessment;
    the severity is the WORST final_severity where an engineer has reviewed it,
    otherwise the AI severity with provisional=True; also count assessments pending review.
    For inspectors: if latest inspection is not assigned to them, severity details are 'restricted'.
    """
    # Find inspections for this asset that have at least one severity assessment
    subq = (
        select(Image.inspection_id)
        .join(SeverityAssessment, SeverityAssessment.image_id == Image.image_id)
        .filter(SeverityAssessment.is_superseded == False)
        .distinct()
    )

    latest_insp = (
        db.query(Inspection)
        .filter(Inspection.asset_id == asset.asset_id, Inspection.inspection_id.in_(subq))
        .order_by(Inspection.inspection_date.desc(), Inspection.inspection_id.desc())
        .first()
    )

    # Calculate overdue flag
    today = date.today()
    is_overdue = False
    if asset.next_inspection_due and asset.next_inspection_due < today:
        is_overdue = True
    elif latest_insp:
        days_since = (today - latest_insp.inspection_date).days
        if days_since > (asset.inspection_frequency_days or 365):
            is_overdue = True
    else:
        # Check if asset has any inspection
        any_insp = db.query(Inspection).filter(Inspection.asset_id == asset.asset_id).order_by(Inspection.inspection_date.desc()).first()
        if any_insp:
            days_since = (today - any_insp.inspection_date).days
            if days_since > (asset.inspection_frequency_days or 365):
                is_overdue = True
        else:
            is_overdue = True

    if not latest_insp:
        return {
            "severity": "none",
            "score": 0.0,
            "provisional": False,
            "pending_review_count": 0,
            "last_inspection_date": None,
            "latest_inspection_id": None,
            "is_overdue": is_overdue,
            "priority": None,
            "review_status": "uninspected",
        }

    # Role check: inspector can only see details for their own inspections
    is_inspector = current_user.role == "inspector"
    is_assigned = latest_insp.inspector_id == current_user.user_id

    if is_inspector and not is_assigned:
        return {
            "severity": "restricted",
            "score": None,
            "provisional": None,
            "pending_review_count": None,
            "last_inspection_date": latest_insp.inspection_date.isoformat(),
            "latest_inspection_id": latest_insp.inspection_id,
            "is_overdue": is_overdue,
            "priority": None,
            "review_status": "restricted",
        }

    # Load assessments for latest_insp
    assessments = (
        db.query(SeverityAssessment)
        .join(Image, Image.image_id == SeverityAssessment.image_id)
        .filter(Image.inspection_id == latest_insp.inspection_id, SeverityAssessment.is_superseded == False)
        .all()
    )

    pending_count = sum(1 for a in assessments if a.review_status == "pending")
    reviewed_assessments = [a for a in assessments if a.review_status == "reviewed" and a.final_severity]

    confirmed_priority = None
    # Check maintenance_priorities table if present
    try:
        from app.models.maintenance import MaintenancePriority
        mp = (
            db.query(MaintenancePriority)
            .filter(MaintenancePriority.asset_id == asset.asset_id, MaintenancePriority.status == "confirmed")
            .order_by(MaintenancePriority.priority_id.desc())
            .first()
        )
        if mp and mp.final_priority:
            confirmed_priority = mp.final_priority
    except Exception:
        pass

    if reviewed_assessments:
        worst_reviewed = max(reviewed_assessments, key=lambda a: SEVERITY_RANKS.get(a.final_severity.lower(), 0))
        severity = worst_reviewed.final_severity.lower()
        score = worst_reviewed.score
        provisional = False
        review_status = "reviewed"
        if not confirmed_priority and worst_reviewed.final_priority:
            confirmed_priority = worst_reviewed.final_priority
    elif assessments:
        worst_ai = max(assessments, key=lambda a: SEVERITY_RANKS.get(a.severity_level.lower(), 0))
        severity = worst_ai.severity_level.lower()
        score = worst_ai.score
        provisional = True
        review_status = "pending"
    else:
        severity = "none"
        score = 0.0
        provisional = False
        review_status = "no_assessments"

    return {
        "severity": severity,
        "score": score,
        "provisional": provisional,
        "pending_review_count": pending_count,
        "last_inspection_date": latest_insp.inspection_date.isoformat(),
        "latest_inspection_id": latest_insp.inspection_id,
        "is_overdue": is_overdue,
        "priority": confirmed_priority,
        "review_status": review_status,
    }


# ------------------------------------------------------------------------------
# 1. GET /map/assets
# ------------------------------------------------------------------------------
@router.get("/assets")
def get_map_assets(
    asset_type: Optional[str] = Query(None),
    severity: Optional[List[str]] = Query(None),
    district: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    review_status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    min_lat: Optional[float] = Query(None),
    min_lon: Optional[float] = Query(None),
    max_lat: Optional[float] = Query(None),
    max_lon: Optional[float] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns GeoJSON FeatureCollection of infrastructure assets with their current condition.
    """
    validate_bbox(min_lat, min_lon, max_lat, max_lon)

    query = db.query(InfrastructureAsset)

    if asset_type:
        query = query.filter(InfrastructureAsset.asset_type == asset_type)
    if district:
        query = query.filter(InfrastructureAsset.district.ilike(f"%{district.strip()}%"))

    if min_lat is not None and max_lat is not None and min_lon is not None and max_lon is not None:
        query = query.filter(
            InfrastructureAsset.latitude >= min_lat,
            InfrastructureAsset.latitude <= max_lat,
            InfrastructureAsset.longitude >= min_lon,
            InfrastructureAsset.longitude <= max_lon,
        )

    all_assets = query.all()

    # Process features and apply condition/inspection filters
    features = []
    sev_filter_set = set(s.lower() for s in severity) if severity else None

    for asset in all_assets:
        cond = get_asset_current_condition(asset, db, current_user)

        # Apply severity filter
        if sev_filter_set and cond["severity"].lower() not in sev_filter_set:
            continue

        # Apply date filters based on last_inspection_date
        if cond["last_inspection_date"]:
            insp_date = date.fromisoformat(cond["last_inspection_date"])
            if date_from and insp_date < date_from:
                continue
            if date_to and insp_date > date_to:
                continue
        elif date_from or date_to:
            continue

        # Apply review_status filter
        if review_status:
            if review_status == "pending" and not cond["provisional"]:
                continue
            if review_status == "reviewed" and cond["provisional"]:
                continue

        # Apply priority filter
        if priority and cond["priority"] != priority:
            continue

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(asset.longitude), float(asset.latitude)],
            },
            "properties": {
                "id": asset.asset_id,
                "name": asset.name,
                "type": asset.asset_type,
                "material": asset.material_type,
                "district": asset.district or "Unknown",
                "current_condition": {
                    "severity": cond["severity"],
                    "score": cond["score"],
                    "provisional": cond["provisional"],
                    "pending_review_count": cond["pending_review_count"],
                    "last_inspection_date": cond["last_inspection_date"],
                },
                "latest_inspection_id": cond["latest_inspection_id"],
                "priority": cond["priority"],
                "overdue": cond["is_overdue"],
            },
        }
        features.append(feature)

    total_count = len(features)
    paginated_features = features[offset : offset + limit]

    return {
        "type": "FeatureCollection",
        "features": paginated_features,
        "metadata": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
        },
    }


# ------------------------------------------------------------------------------
# 2. GET /map/damage
# ------------------------------------------------------------------------------
@router.get("/damage")
def get_map_damage(
    asset_type: Optional[str] = Query(None),
    severity: Optional[List[str]] = Query(None),
    district: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    min_lat: Optional[float] = Query(None),
    min_lon: Optional[float] = Query(None),
    max_lat: Optional[float] = Query(None),
    max_lon: Optional[float] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns GeoJSON Point features for damage markers built from image GPS (EXIF).
    Falls back to asset location with location_source="asset" when image has no GPS.
    """
    validate_bbox(min_lat, min_lon, max_lat, max_lon)

    # Query severity assessments that are not superseded
    query = (
        db.query(SeverityAssessment, Image, Inspection, InfrastructureAsset)
        .join(Image, Image.image_id == SeverityAssessment.image_id)
        .join(Inspection, Inspection.inspection_id == Image.inspection_id)
        .join(InfrastructureAsset, InfrastructureAsset.asset_id == Inspection.asset_id)
        .filter(SeverityAssessment.is_superseded == False)
    )

    if asset_type:
        query = query.filter(InfrastructureAsset.asset_type == asset_type)
    if district:
        query = query.filter(InfrastructureAsset.district.ilike(f"%{district.strip()}%"))
    if date_from:
        query = query.filter(Inspection.inspection_date >= date_from)
    if date_to:
        query = query.filter(Inspection.inspection_date <= date_to)

    sev_filter_set = set(s.lower() for s in severity) if severity else None

    records = query.all()
    features = []
    is_inspector = current_user.role == "inspector"

    for sa, img, insp, asset in records:
        # Determine coordinates: image EXIF GPS first, asset fallback second
        if img.gps_latitude is not None and img.gps_longitude is not None:
            lat = float(img.gps_latitude)
            lon = float(img.gps_longitude)
            loc_source = "image_exif"
        elif asset.latitude is not None and asset.longitude is not None:
            lat = float(asset.latitude)
            lon = float(asset.longitude)
            loc_source = "asset"
        else:
            continue  # Never invent a location

        # Bbox filter on resolved coordinates
        if min_lat is not None and max_lat is not None and min_lon is not None and max_lon is not None:
            if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
                continue

        # Severity resolution
        if sa.review_status == "reviewed" and sa.final_severity:
            sev_level = sa.final_severity.lower()
            provisional = False
        else:
            sev_level = sa.severity_level.lower()
            provisional = True

        if sev_filter_set and sev_level not in sev_filter_set:
            continue

        # Check inspector role restriction
        if is_inspector and insp.inspector_id != current_user.user_id:
            props_severity = "restricted"
            props_score = None
            props_damage_types = ["restricted"]
            props_detection_count = 0
            props_provisional = None
        else:
            props_severity = sev_level
            props_score = sa.score
            props_provisional = provisional

            # Find detections for this run
            detections = db.query(Detection).filter(Detection.run_id == sa.run_id).all()
            dmg_types = list({d.damage_type for d in detections if d.damage_type})
            props_damage_types = dmg_types if dmg_types else ["crack"]
            props_detection_count = len(detections)

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat],
            },
            "properties": {
                "assessment_id": sa.assessment_id,
                "image_id": img.image_id,
                "inspection_id": insp.inspection_id,
                "asset_id": asset.asset_id,
                "asset_name": asset.name,
                "severity": props_severity,
                "score": props_score,
                "provisional": props_provisional,
                "damage_types": props_damage_types,
                "detection_count": props_detection_count,
                "date": insp.inspection_date.isoformat(),
                "location_source": loc_source,
            },
        }
        features.append(feature)

    total_count = len(features)
    paginated = features[offset : offset + limit]

    return {
        "type": "FeatureCollection",
        "features": paginated,
        "metadata": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
        },
    }


# ------------------------------------------------------------------------------
# 3. GET /map/hotspots
# ------------------------------------------------------------------------------
@router.get("/hotspots")
def get_map_hotspots(
    grid_size: float = Query(0.01, ge=0.001, le=1.0, description="Grid aggregation cell size in degrees"),
    asset_type: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    min_lat: Optional[float] = Query(None),
    min_lon: Optional[float] = Query(None),
    max_lat: Optional[float] = Query(None),
    max_lon: Optional[float] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns weighted damage points and grid aggregated cells for heatmap visualization.
    weight = severity_score / 100.
    """
    validate_bbox(min_lat, min_lon, max_lat, max_lon)

    query = (
        db.query(SeverityAssessment, Image, Inspection, InfrastructureAsset)
        .join(Image, Image.image_id == SeverityAssessment.image_id)
        .join(Inspection, Inspection.inspection_id == Image.inspection_id)
        .join(InfrastructureAsset, InfrastructureAsset.asset_id == Inspection.asset_id)
        .filter(SeverityAssessment.is_superseded == False)
    )

    if asset_type:
        query = query.filter(InfrastructureAsset.asset_type == asset_type)
    if district:
        query = query.filter(InfrastructureAsset.district.ilike(f"%{district.strip()}%"))
    if date_from:
        query = query.filter(Inspection.inspection_date >= date_from)
    if date_to:
        query = query.filter(Inspection.inspection_date <= date_to)

    records = query.all()
    points = []
    grid_cells: Dict[str, Dict[str, Any]] = {}

    is_inspector = current_user.role == "inspector"

    for sa, img, insp, asset in records:
        if is_inspector and insp.inspector_id != current_user.user_id:
            continue

        if img.gps_latitude is not None and img.gps_longitude is not None:
            lat = float(img.gps_latitude)
            lon = float(img.gps_longitude)
        elif asset.latitude is not None and asset.longitude is not None:
            lat = float(asset.latitude)
            lon = float(asset.longitude)
        else:
            continue

        if min_lat is not None and max_lat is not None and min_lon is not None and max_lon is not None:
            if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
                continue

        score = float(sa.score or 0.0)
        weight = max(0.05, min(1.0, score / 100.0))
        sev = sa.final_severity.lower() if (sa.review_status == "reviewed" and sa.final_severity) else sa.severity_level.lower()

        points.append({
            "lat": lat,
            "lon": lon,
            "weight": round(weight, 4),
            "score": score,
            "severity": sev,
        })

        # Grid aggregation
        cell_lat = round(lat / grid_size) * grid_size
        cell_lon = round(lon / grid_size) * grid_size
        cell_key = f"{cell_lat:.5f}_{cell_lon:.5f}"

        if cell_key not in grid_cells:
            grid_cells[cell_key] = {
                "cell_centre": [round(cell_lat, 5), round(cell_lon, 5)],
                "count": 0,
                "scores": [],
                "max_sev_rank": 0,
            }

        cell = grid_cells[cell_key]
        cell["count"] += 1
        cell["scores"].append(score)
        rank = SEVERITY_RANKS.get(sev, 0)
        if rank > cell["max_sev_rank"]:
            cell["max_sev_rank"] = rank

    aggregated = []
    for cell in grid_cells.values():
        mean_score = sum(cell["scores"]) / len(cell["scores"]) if cell["scores"] else 0.0
        aggregated.append({
            "cell_centre": cell["cell_centre"],
            "count": cell["count"],
            "mean_score": round(mean_score, 2),
            "max_severity": RANK_TO_SEVERITY.get(cell["max_sev_rank"], "none"),
        })

    return {
        "points": points,
        "grid": aggregated,
        "grid_size": grid_size,
        "total_points": len(points),
    }


# ------------------------------------------------------------------------------
# 4. GET /map/summary
# ------------------------------------------------------------------------------
@router.get("/summary")
def get_map_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Region-wise summaries (grouped by district, or by asset type if district is empty).
    """
    assets = db.query(InfrastructureAsset).all()

    # Group by district
    groups: Dict[str, List[InfrastructureAsset]] = {}
    for a in assets:
        key = a.district.strip() if a.district and a.district.strip() else f"Type: {a.asset_type.capitalize()}"
        groups.setdefault(key, []).append(a)

    summary_rows = []
    for region_name, group_assets in groups.items():
        counts = {"none": 0, "minor": 0, "moderate": 0, "severe": 0, "critical": 0, "restricted": 0}
        scores = []
        overdue_count = 0
        pending_count = 0

        for a in group_assets:
            cond = get_asset_current_condition(a, db, current_user)
            sev = cond["severity"].lower()
            if sev in counts:
                counts[sev] += 1
            else:
                counts["none"] += 1

            if cond["score"] is not None:
                scores.append(cond["score"])
            if cond["is_overdue"]:
                overdue_count += 1
            if cond["pending_review_count"] and cond["pending_review_count"] > 0:
                pending_count += cond["pending_review_count"]

        mean_score = round(sum(scores) / len(scores), 2) if scores else 0.0

        summary_rows.append({
            "region": region_name,
            "total_assets": len(group_assets),
            "counts_per_severity": counts,
            "mean_score": mean_score,
            "number_overdue": overdue_count,
            "number_pending_review": pending_count,
        })

    summary_rows.sort(key=lambda r: r["total_assets"], reverse=True)
    return {"regions": summary_rows, "total_regions": len(summary_rows)}


# ------------------------------------------------------------------------------
# 5. GET /map/route
# ------------------------------------------------------------------------------
@router.get("/route")
def get_inspector_route(
    inspector_id: int = Query(..., description="ID of inspector to route"),
    route_date: date = Query(..., alias="date", description="Inspection date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Calculates ordered inspection stops using nearest-neighbour haversine distance.
    Roles allowed: manager, civil_engineer, admin, or the inspector themself.
    """
    if current_user.role == "inspector" and current_user.user_id != inspector_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inspectors can only view their own inspection routes.",
        )

    # Fetch inspections for this inspector on route_date
    inspections = (
        db.query(Inspection, InfrastructureAsset)
        .join(InfrastructureAsset, InfrastructureAsset.asset_id == Inspection.asset_id)
        .filter(Inspection.inspector_id == inspector_id, Inspection.inspection_date == route_date)
        .order_by(Inspection.inspection_id.asc())
        .all()
    )

    if not inspections:
        return {
            "inspector_id": inspector_id,
            "date": route_date.isoformat(),
            "ordered_stops": [],
            "total_distance_km": 0.0,
            "distance_label": "straight-line order, not a road route",
            "message": "No scheduled inspections found for this inspector on the specified date.",
        }

    # Extract unique asset stops
    raw_stops = []
    seen_assets = set()
    for insp, asset in inspections:
        if asset.asset_id not in seen_assets:
            seen_assets.add(asset.asset_id)
            raw_stops.append({
                "asset_id": asset.asset_id,
                "asset_name": asset.name,
                "asset_type": asset.asset_type,
                "inspection_id": insp.inspection_id,
                "lat": float(asset.latitude),
                "lon": float(asset.longitude),
                "district": asset.district or "Unknown",
            })

    # Nearest-neighbour tour starting from first stop
    ordered = [raw_stops[0]]
    remaining = raw_stops[1:]
    total_km = 0.0

    curr = ordered[0]
    while remaining:
        best_idx = 0
        best_dist = haversine_km(curr["lat"], curr["lon"], remaining[0]["lat"], remaining[0]["lon"])

        for i in range(1, len(remaining)):
            d = haversine_km(curr["lat"], curr["lon"], remaining[i]["lat"], remaining[i]["lon"])
            if d < best_dist:
                best_dist = d
                best_idx = i

        total_km += best_dist
        curr = remaining.pop(best_idx)
        ordered.append(curr)

    # Format output with step numbers
    for idx, stop in enumerate(ordered, start=1):
        stop["stop_number"] = idx

    return {
        "inspector_id": inspector_id,
        "date": route_date.isoformat(),
        "ordered_stops": ordered,
        "total_distance_km": round(total_km, 2),
        "distance_label": "straight-line order, not a road route",
    }
