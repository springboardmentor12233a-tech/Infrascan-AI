
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import sqlite3

from database import get_connection
from auth import get_current_user, require_role


router = APIRouter(prefix="/assets", tags=["Asset Management"])


# Roles permitted to create and update assets
ASSET_MANAGERS = (
    "Admin",
)


# Initialize the assets table
def initialize_assets_table():
    connection = get_connection()

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                location TEXT NOT NULL,
                construction_year INTEGER,
                material TEXT NOT NULL,
                department TEXT NOT NULL,
                inspection_frequency TEXT NOT NULL,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)

        # Add GPS columns to existing databases if they are missing
        columns = [
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(assets)"
            ).fetchall()
        ]

        if "latitude" not in columns:
            connection.execute(
                "ALTER TABLE assets ADD COLUMN latitude REAL"
            )

        if "longitude" not in columns:
            connection.execute(
                "ALTER TABLE assets ADD COLUMN longitude REAL"
            )

        connection.commit()

    finally:
        connection.close()


# Create the table when this module is loaded
initialize_assets_table()


# Request model for creating an asset
class AssetCreate(BaseModel):
    asset_code: str = Field(min_length=2, max_length=30)
    name: str = Field(min_length=2, max_length=120)
    asset_type: str = Field(min_length=2, max_length=60)
    location: str = Field(min_length=2, max_length=200)

    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)

    construction_year: Optional[int] = Field(
        default=None, ge=1800, le=2100
    )
    material: str = Field(min_length=2, max_length=80)
    department: str = Field(min_length=2, max_length=100)
    inspection_frequency: str = Field(min_length=2, max_length=50)


# Request model for updating an asset
class AssetUpdate(BaseModel):
    asset_code: Optional[str] = Field(
        default=None, min_length=2, max_length=30
    )
    name: Optional[str] = Field(
        default=None, min_length=2, max_length=120
    )
    asset_type: Optional[str] = Field(
        default=None, min_length=2, max_length=60
    )
    location: Optional[str] = Field(
        default=None, min_length=2, max_length=200
    )
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)

    construction_year: Optional[int] = Field(
        default=None, ge=1800, le=2100
    )
    material: Optional[str] = Field(
        default=None, min_length=2, max_length=80
    )
    department: Optional[str] = Field(
        default=None, min_length=2, max_length=100
    )
    inspection_frequency: Optional[str] = Field(
        default=None, min_length=2, max_length=50
    )


def asset_to_dict(asset):
    return dict(asset)


# CREATE ASSET
@router.post("/")
def create_asset(
    request: AssetCreate,
    current_user: dict = Depends(require_role(*ASSET_MANAGERS)),
):
    connection = get_connection()

    try:
        cursor = connection.execute(
    """
    INSERT INTO assets (
        asset_code,
        name,
        asset_type,
        location,
        latitude,
        longitude,
        construction_year,
        material,
        department,
        inspection_frequency,
        created_by
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (
        request.asset_code.strip().upper(),
        request.name.strip(),
        request.asset_type.strip(),
        request.location.strip(),
        request.latitude,
        request.longitude,
        request.construction_year,
        request.material.strip(),
        request.department.strip(),
        request.inspection_frequency.strip(),
        current_user["id"],
    ),
)

        connection.commit()

        asset = connection.execute(
            "SELECT * FROM assets WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

        return {
            "message": "Asset created successfully",
            "asset": asset_to_dict(asset),
        }

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="An asset with this asset ID already exists",
        )

    finally:
        connection.close()


# GET ALL ASSETS
@router.get("/")
def get_assets(
    search: Optional[str] = Query(default=None, max_length=120),
    current_user: dict = Depends(get_current_user),
):
    connection = get_connection()

    try:
        if search and search.strip():
            search_value = f"%{search.strip()}%"

            assets = connection.execute(
                """
                SELECT * FROM assets
                WHERE asset_code LIKE ?
                   OR name LIKE ?
                   OR location LIKE ?
                   OR asset_type LIKE ?
                ORDER BY created_at DESC
                """,
                (
                    search_value,
                    search_value,
                    search_value,
                    search_value,
                ),
            ).fetchall()

        else:
            assets = connection.execute(
                """
                SELECT * FROM assets
                ORDER BY created_at DESC
                """
            ).fetchall()

        return {
            "total": len(assets),
            "assets": [asset_to_dict(asset) for asset in assets],
        }

    finally:
        connection.close()


# GET ONE ASSET
@router.get("/{asset_id}")
def get_asset(
    asset_id: int,
    current_user: dict = Depends(get_current_user),
):
    connection = get_connection()

    try:
        asset = connection.execute(
            "SELECT * FROM assets WHERE id = ?",
            (asset_id,),
        ).fetchone()

        if not asset:
            raise HTTPException(
                status_code=404,
                detail="Asset not found",
            )

        return {"asset": asset_to_dict(asset)}

    finally:
        connection.close()


# UPDATE ASSET
@router.put("/{asset_id}")
def update_asset(
    asset_id: int,
    request: AssetUpdate,
    current_user: dict = Depends(require_role(*ASSET_MANAGERS)),
):
    updates = request.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="No update information provided",
        )

    for key, value in updates.items():
        if isinstance(value, str):
            updates[key] = value.strip()

    if "asset_code" in updates and updates["asset_code"]:
        updates["asset_code"] = updates["asset_code"].upper()

    connection = get_connection()

    try:
        existing = connection.execute(
            "SELECT id FROM assets WHERE id = ?",
            (asset_id,),
        ).fetchone()

        if not existing:
            raise HTTPException(
                status_code=404,
                detail="Asset not found",
            )

        columns = ", ".join(
            f"{column} = ?" for column in updates
        )

        values = list(updates.values())
        values.append(asset_id)

        connection.execute(
            f"""
            UPDATE assets
            SET {columns}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            values,
        )

        connection.commit()

        updated_asset = connection.execute(
            "SELECT * FROM assets WHERE id = ?",
            (asset_id,),
        ).fetchone()

        return {
            "message": "Asset updated successfully",
            "asset": asset_to_dict(updated_asset),
        }

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="An asset with this asset ID already exists",
        )

    finally:
        connection.close()


# DELETE ASSET
@router.delete("/{asset_id}")
def delete_asset(
    asset_id: int,
    current_user: dict = Depends(
        require_role("Admin")
    ),
):
    connection = get_connection()

    try:
        existing = connection.execute(
            "SELECT id FROM assets WHERE id = ?",
            (asset_id,),
        ).fetchone()

        if not existing:
            raise HTTPException(
                status_code=404,
                detail="Asset not found",
            )

        connection.execute(
            "DELETE FROM assets WHERE id = ?",
            (asset_id,),
        )

        connection.commit()

        return {"message": "Asset deleted successfully"}

    finally:
        connection.close()
