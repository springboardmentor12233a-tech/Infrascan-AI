"""
models/__init__.py – imports all models so SQLAlchemy sees them when
Base.metadata.create_all() is called.

If you add a new model file, import it here too.
"""

from app.models.role import Role, ROLE_NAMES           # noqa: F401
from app.models.user import User                        # noqa: F401
from app.models.infrastructure_asset import (           # noqa: F401
    InfrastructureAsset, AssetType
)
from app.models.inspection import Inspection, InspectionStatus  # noqa: F401
from app.models.inspection_image import (               # noqa: F401
    InspectionImage, QualityStatus
)
from app.models.audit_log import AuditLog               # noqa: F401
