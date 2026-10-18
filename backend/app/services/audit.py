from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from typing import Optional


def log_action(
    db: Session,
    action: str,
    entity: str,
    entity_id: Optional[str] = None,
    user_id: Optional[int] = None
) -> AuditLog:
    """Creates and persists an audit log record."""
    log_entry = AuditLog(
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=str(entity_id) if entity_id is not None else None
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry
