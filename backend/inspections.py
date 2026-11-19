from datetime import date
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from database import get_connection
from auth import get_current_user, require_role


router = APIRouter(
    prefix="/inspections",
    tags=["Inspection Management"],
)

INSPECTION_MANAGERS = ("Admin",)

INSPECTION_STATUSES = (
    "Scheduled",
    "In Progress",
    "Completed",
    "Cancelled",
)


# --------------------------------------------------
# DATABASE TABLE
# --------------------------------------------------

def initialize_inspections_table():
    connection = get_connection()

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS inspections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inspection_code TEXT NOT NULL UNIQUE,
                asset_id INTEGER NOT NULL,
                inspection_date TEXT NOT NULL,
                inspection_type TEXT NOT NULL,
                assigned_inspector_id INTEGER,
                status TEXT NOT NULL DEFAULT 'Scheduled',
                notes TEXT,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (asset_id)
                    REFERENCES assets(id),

                FOREIGN KEY (assigned_inspector_id)
                    REFERENCES users(id),

                FOREIGN KEY (created_by)
                    REFERENCES users(id)
            )
        """)

        connection.commit()

    finally:
        connection.close()


initialize_inspections_table()


# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class InspectionCreate(BaseModel):
    inspection_code: str = Field(min_length=3, max_length=40)
    asset_id: int = Field(gt=0)
    inspection_date: date
    inspection_type: str = Field(min_length=2, max_length=80)
    assigned_inspector_id: Optional[int] = Field(default=None, gt=0)

    status: Literal[
        "Scheduled",
        "In Progress",
        "Completed",
        "Cancelled",
    ] = "Scheduled"

    notes: Optional[str] = Field(default=None, max_length=2000)


class InspectionUpdate(BaseModel):
    inspection_code: Optional[str] = Field(
        default=None, min_length=3, max_length=40
    )
    asset_id: Optional[int] = Field(default=None, gt=0)
    inspection_date: Optional[date] = None

    inspection_type: Optional[str] = Field(
        default=None, min_length=2, max_length=80
    )

    assigned_inspector_id: Optional[int] = Field(default=None, gt=0)

    status: Optional[
        Literal[
            "Scheduled",
            "In Progress",
            "Completed",
            "Cancelled",
        ]
    ] = None

    notes: Optional[str] = Field(default=None, max_length=2000)


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def validate_asset(connection, asset_id: int):
    asset = connection.execute(
        "SELECT id FROM assets WHERE id = ?",
        (asset_id,),
    ).fetchone()

    if not asset:
        raise HTTPException(
            status_code=404,
            detail="Selected asset was not found",
        )


def validate_inspector(connection, inspector_id: Optional[int]):
    if inspector_id is None:
        return

    inspector = connection.execute(
        """
        SELECT id, role, is_active
        FROM users
        WHERE id = ?
        """,
        (inspector_id,),
    ).fetchone()

    if not inspector or not inspector["is_active"]:
        raise HTTPException(
            status_code=404,
            detail="Assigned user was not found or is inactive",
        )

    if inspector["role"] != "User":
        raise HTTPException(
            status_code=400,
            detail="Select a User account",
        )


def get_inspection_details(connection, inspection_id: int):
    return connection.execute(
        """
        SELECT
            i.*,
            a.asset_code,
            a.name AS asset_name,
            a.asset_type,
            a.location AS asset_location,
            u.full_name AS inspector_name
        FROM inspections i
        JOIN assets a ON a.id = i.asset_id
        LEFT JOIN users u ON u.id = i.assigned_inspector_id
        WHERE i.id = ?
        """,
        (inspection_id,),
    ).fetchone()


def inspection_to_dict(inspection):
    return dict(inspection)


# --------------------------------------------------
# GET AVAILABLE USERS
# --------------------------------------------------

@router.get("/inspectors")
def get_available_inspectors(
    current_user: dict = Depends(get_current_user),
):
    connection = get_connection()

    try:
        inspectors = connection.execute(
            """
            SELECT id, full_name, email, role
            FROM users
            WHERE is_active = 1
              AND role = 'User'
            ORDER BY full_name
            """
        ).fetchall()

        return {
            "total": len(inspectors),
            "inspectors": [dict(item) for item in inspectors],
        }

    finally:
        connection.close()


# --------------------------------------------------
# CREATE INSPECTION - ADMIN ONLY
# --------------------------------------------------

@router.post("/")
def create_inspection(
    request: InspectionCreate,
    current_user: dict = Depends(
        require_role(*INSPECTION_MANAGERS)
    ),
):
    connection = get_connection()

    try:
        validate_asset(connection, request.asset_id)

        validate_inspector(
            connection,
            request.assigned_inspector_id,
        )

        cursor = connection.execute(
            """
            INSERT INTO inspections (
                inspection_code,
                asset_id,
                inspection_date,
                inspection_type,
                assigned_inspector_id,
                status,
                notes,
                created_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.inspection_code.strip().upper(),
                request.asset_id,
                request.inspection_date.isoformat(),
                request.inspection_type.strip(),
                request.assigned_inspector_id,
                request.status,
                request.notes.strip() if request.notes else None,
                current_user["id"],
            ),
        )

        connection.commit()

        inspection = get_inspection_details(
            connection,
            cursor.lastrowid,
        )

        return {
            "message": "Inspection created successfully",
            "inspection": inspection_to_dict(inspection),
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# --------------------------------------------------
# GET ALL INSPECTIONS - ADMIN AND USER
# --------------------------------------------------

@router.get("/")
def get_inspections(
    search: Optional[str] = Query(default=None, max_length=120),
    status: Optional[str] = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    if status and status not in INSPECTION_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Invalid inspection status",
        )

    connection = get_connection()

    try:
        query = """
            SELECT
                i.*,
                a.asset_code,
                a.name AS asset_name,
                a.asset_type,
                a.location AS asset_location,
                u.full_name AS inspector_name
            FROM inspections i
            JOIN assets a ON a.id = i.asset_id
            LEFT JOIN users u ON u.id = i.assigned_inspector_id
            WHERE 1 = 1
        """

        parameters = []

        if search and search.strip():
            search_value = f"%{search.strip()}%"

            query += """
                AND (
                    i.inspection_code LIKE ?
                    OR a.name LIKE ?
                    OR a.asset_code LIKE ?
                    OR a.location LIKE ?
                )
            """

            parameters.extend([
                search_value,
                search_value,
                search_value,
                search_value,
            ])

        if status:
            query += " AND i.status = ?"
            parameters.append(status)

        query += " ORDER BY i.created_at DESC"

        inspections = connection.execute(
            query,
            parameters,
        ).fetchall()

        return {
            "total": len(inspections),
            "inspections": [
                inspection_to_dict(item)
                for item in inspections
            ],
        }

    finally:
        connection.close()


# --------------------------------------------------
# GET ONE INSPECTION - ADMIN AND USER
# --------------------------------------------------

@router.get("/{inspection_id}")
def get_inspection(
    inspection_id: int,
    current_user: dict = Depends(get_current_user),
):
    connection = get_connection()

    try:
        inspection = get_inspection_details(
            connection,
            inspection_id,
        )

        if not inspection:
            raise HTTPException(
                status_code=404,
                detail="Inspection not found",
            )

        return {
            "inspection": inspection_to_dict(inspection),
        }

    finally:
        connection.close()


# --------------------------------------------------
# UPDATE INSPECTION - ADMIN ONLY
# --------------------------------------------------

@router.put("/{inspection_id}")
def update_inspection(
    inspection_id: int,
    request: InspectionUpdate,
    current_user: dict = Depends(
        require_role(*INSPECTION_MANAGERS)
    ),
):
    updates = request.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="No update information provided",
        )

    if "inspection_code" in updates and updates["inspection_code"]:
        updates["inspection_code"] = (
            updates["inspection_code"].strip().upper()
        )

    if "inspection_type" in updates and updates["inspection_type"]:
        updates["inspection_type"] = updates["inspection_type"].strip()

    if "inspection_date" in updates and updates["inspection_date"]:
        updates["inspection_date"] = (
            updates["inspection_date"].isoformat()
        )

    if "notes" in updates and updates["notes"]:
        updates["notes"] = updates["notes"].strip()

    connection = get_connection()

    try:
        existing = connection.execute(
            "SELECT id FROM inspections WHERE id = ?",
            (inspection_id,),
        ).fetchone()

        if not existing:
            raise HTTPException(
                status_code=404,
                detail="Inspection not found",
            )

        if updates.get("asset_id") is not None:
            validate_asset(connection, updates["asset_id"])

        if "assigned_inspector_id" in updates:
            validate_inspector(
                connection,
                updates["assigned_inspector_id"],
            )

        columns = ", ".join(
            f"{column} = ?" for column in updates
        )

        values = list(updates.values())
        values.append(inspection_id)

        connection.execute(
            f"""
            UPDATE inspections
            SET {columns},
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            values,
        )

        connection.commit()

        inspection = get_inspection_details(
            connection,
            inspection_id,
        )

        return {
            "message": "Inspection updated successfully",
            "inspection": inspection_to_dict(inspection),
        }

    finally:
        connection.close()


# --------------------------------------------------
# DELETE INSPECTION - ADMIN ONLY
# --------------------------------------------------

@router.delete("/{inspection_id}")
def delete_inspection(
    inspection_id: int,
    current_user: dict = Depends(
        require_role("Admin")
    ),
):
    connection = get_connection()

    try:
        existing = connection.execute(
            "SELECT id FROM inspections WHERE id = ?",
            (inspection_id,),
        ).fetchone()

        if not existing:
            raise HTTPException(
                status_code=404,
                detail="Inspection not found",
            )

        connection.execute(
            "DELETE FROM inspections WHERE id = ?",
            (inspection_id,),
        )

        connection.commit()

        return {
            "message": "Inspection deleted successfully",
        }

    finally:
        connection.close()