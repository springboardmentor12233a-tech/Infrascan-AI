"""
services/seed.py – Seeds roles, demo work orders, and safety notifications.
"""
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models.role import Role, ROLE_NAMES
from app.models.work_order import WorkOrder, WorkOrderStatus, WorkOrderPriority
from app.models.notification import Notification, AlertLevel
from app.models.infrastructure_asset import InfrastructureAsset
from app.models.user import User


def seed_roles(db: Session) -> None:
    """Insert the 5 roles if they don't exist yet."""
    for name in ROLE_NAMES:
        exists = db.query(Role).filter(Role.name == name).first()
        if not exists:
            db.add(Role(name=name))
    db.commit()

    # Seed sample work orders if none exist and assets exist
    if db.query(WorkOrder).count() == 0:
        asset = db.query(InfrastructureAsset).first()
        maintenance_user = db.query(User).filter(User.email.like("%maintenance%")).first()
        if asset:
            db.add_all([
                WorkOrder(
                    asset_id=asset.id,
                    assigned_to_id=maintenance_user.id if maintenance_user else None,
                    title=f"Epoxy Pressure Grouting – {asset.name}",
                    description="Seal 3.8mm shear diagonal crack along pier cap support beam to stop moisture ingress.",
                    priority=WorkOrderPriority.HIGH,
                    status=WorkOrderStatus.IN_PROGRESS,
                    estimated_cost=4200.0,
                    due_date=date.today() + timedelta(days=14)
                ),
                WorkOrder(
                    asset_id=asset.id,
                    assigned_to_id=maintenance_user.id if maintenance_user else None,
                    title="Rebar Corrosion Passivation & Patching",
                    description="Chipping loose spalled concrete, applying zinc-rich anti-corrosion primer to exposed steel bars.",
                    priority=WorkOrderPriority.CRITICAL,
                    status=WorkOrderStatus.OPEN,
                    estimated_cost=8500.0,
                    due_date=date.today() + timedelta(days=7)
                ),
                WorkOrder(
                    asset_id=asset.id,
                    assigned_to_id=maintenance_user.id if maintenance_user else None,
                    title="Drainage Weep Hole Clearing & Efflorescence Removal",
                    description="High-pressure washing of calcium efflorescence leaching and unblocking soffit weep holes.",
                    priority=WorkOrderPriority.LOW,
                    status=WorkOrderStatus.RESOLVED,
                    estimated_cost=1200.0,
                    due_date=date.today() - timedelta(days=5),
                    resolution_notes="Completed weep hole flush and neutralizer application."
                )
            ])
            db.commit()

    # Seed sample notifications if none exist
    if db.query(Notification).count() == 0:
        db.add_all([
            Notification(
                target_role="Civil Engineer",
                title="Critical Crack Growth Detected",
                message="AI analysis on BRG-001 (Golden Gate Overpass Viaduct) detected crack width expansion to 3.8mm (+18% growth). Engineering review required.",
                alert_level=AlertLevel.CRITICAL,
                link="/maintenance",
                is_read=False
            ),
            Notification(
                target_role="Infrastructure Inspector",
                title="Scheduled Field Inspection Due",
                message="Pine Valley Reservoir Gravity Dam (DAM-003) is due for semi-annual optical surface assessment.",
                alert_level=AlertLevel.MEDIUM,
                link="/assets/3",
                is_read=False
            ),
            Notification(
                target_role="Maintenance Engineer",
                title="New Work Order Assigned: Rebar Passivation",
                message="Priority repair work order assigned to Maintenance Department for pier cap spalling.",
                alert_level=AlertLevel.HIGH,
                link="/maintenance",
                is_read=False
            ),
            Notification(
                target_role=None,
                title="InfraScan AI Model v3.0 Online",
                message="Multi-model ensemble running MobileNetV3 + Grad-CAM++ with 94.6% benchmark defect accuracy.",
                alert_level=AlertLevel.INFORMATIONAL,
                link="/model-comparison",
                is_read=True
            )
        ])
        db.commit()
