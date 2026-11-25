import json
import logging
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.asset import InfrastructureAsset
from app.models.maintenance import MaintenanceTask
from app.models.notification import Notification, NotificationPreference
from app.models.user import User
from app.services.event_service import publish

logger = logging.getLogger(__name__)

RULES_PATH = Path(__file__).resolve().parent.parent / "config" / "notification_rules.json"

SEVERITY_LEVELS = {
    "none": 0,
    "low": 1,
    "minor": 1,
    "medium": 2,
    "moderate": 2,
    "high": 3,
    "severe": 3,
    "critical": 4,
}


def load_notification_rules() -> Dict[str, Any]:
    """Load notification event definitions and deduplication settings."""
    if RULES_PATH.exists():
        try:
            with open(RULES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read notification rules from {RULES_PATH}: {e}")
    return {"deduplication_window_seconds": 3600, "events": {}}


def get_or_create_preference(db: Session, user_id: int) -> NotificationPreference:
    """Retrieve existing user notification preference or insert default."""
    pref = db.query(NotificationPreference).filter(NotificationPreference.user_id == user_id).first()
    if not pref:
        pref = NotificationPreference(
            user_id=user_id,
            in_app_enabled=True,
            email_enabled=True,
            min_severity="low",
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref


def send_email_notification(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
) -> bool:
    """Send email via SMTP with full failure isolation. Never raises an exception."""
    if not settings.EMAIL_ENABLED:
        logger.info(f"[EMAIL DISABLED] Would send to {to_email}: {subject}")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to_email

        # Always attach engineering disclaimer
        disclaimer = "\n\n---\nDisclaimer: AI result for engineer review, not a final structural safety verdict."
        full_text = body_text + disclaimer
        msg.attach(MIMEText(full_text, "plain", "utf-8"))

        if body_html:
            html_disclaimer = "<hr><p style='font-size:11px;color:#64748B;'>Disclaimer: AI result for engineer review, not a final structural safety verdict.</p>"
            msg.attach(MIMEText(body_html + html_disclaimer, "html", "utf-8"))

        # In testing or when no host, simulate delivery
        import os
        if os.getenv("TESTING") == "1" or settings.SMTP_HOST in ("none", "disabled", "test"):
            logger.info(f"[EMAIL SIMULATED] Sent to {to_email}: {subject}")
            return True

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=5) as server:
            if settings.SMTP_TLS:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            logger.info(f"Email sent successfully to {to_email}")
            return True
    except Exception as e:
        logger.warning(f"Failed to send email to {to_email} via {settings.SMTP_HOST}:{settings.SMTP_PORT}: {e}")
        return False


def create_notification(
    db: Session,
    user_id: int,
    type: str,
    title: str,
    body: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    severity: Optional[str] = None,
) -> Optional[Notification]:
    """Create in-app notification with deduplication and dispatch email respecting user preferences."""
    rules = load_notification_rules()
    dedup_window = rules.get("deduplication_window_seconds", 3600)

    # 1. Deduplication check
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=dedup_window)
    existing = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.type == type,
            Notification.entity_type == entity_type,
            Notification.entity_id == str(entity_id) if entity_id is not None else None,
            Notification.created_at >= cutoff,
        )
        .first()
    )
    if existing:
        logger.debug(f"Suppressed duplicate notification for user {user_id}, type {type}, entity {entity_type}#{entity_id}")
        return existing

    # 2. Check user preferences
    pref = get_or_create_preference(db, user_id)

    # Check minimum severity threshold if provided
    if severity:
        sev_rank = SEVERITY_LEVELS.get(severity.lower(), 1)
        pref_rank = SEVERITY_LEVELS.get(pref.min_severity.lower(), 1)
        if sev_rank < pref_rank:
            logger.debug(f"Notification suppressed: severity {severity} below user preference {pref.min_severity}")
            return None

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user or not user.is_active:
        return None

    # 3. Create In-App Notification
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
    )
    db.add(notification)
    publish(
        db=db,
        event_type="notification.created",
        entity_type="notification",
        entity_id=notification.id or 0,
        audience={"user_ids": [user_id]},
        payload={
            "id": notification.id,
            "user_id": user_id,
            "type": type,
            "title": title,
            "body": body,
            "entity_type": entity_type,
            "entity_id": str(entity_id) if entity_id is not None else None,
        },
    )
    db.commit()
    db.refresh(notification)

    # 4. Dispatch Email if enabled
    if pref.email_enabled and user.email:
        sent = send_email_notification(
            to_email=user.email,
            subject=f"[InfraScan] {title}",
            body_text=body,
        )
        if sent:
            notification.email_sent = True
            notification.email_sent_at = datetime.now(timezone.utc)
            db.commit()

    return notification


def notify_roles(
    db: Session,
    type: str,
    title: str,
    body: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    severity: Optional[str] = None,
    extra_roles: Optional[List[str]] = None,
) -> List[Notification]:
    """Find all active users with target roles for an event and create individual notifications."""
    rules = load_notification_rules()
    event_rule = rules.get("events", {}).get(type, {})
    target_roles = set(event_rule.get("target_roles", []))
    if extra_roles:
        target_roles.update(extra_roles)

    if not target_roles:
        target_roles = {"admin", "civil_engineer"}

    users = db.query(User).filter(User.role.in_(list(target_roles)), User.is_active == True).all()
    created = []
    for u in users:
        n = create_notification(
            db=db,
            user_id=u.user_id,
            type=type,
            title=title,
            body=body,
            entity_type=entity_type,
            entity_id=entity_id,
            severity=severity,
        )
        if n:
            created.append(n)
    return created


def sweep_deadlines_and_overdue(db: Session) -> Dict[str, int]:
    """Sweep background maintenance deadlines and overdue inspections to generate alert notifications."""
    now = datetime.now(timezone.utc)
    summary = {"maintenance_alerts": 0, "overdue_inspections": 0}

    # 1. Maintenance tasks due within 48 hours
    upcoming_limit = (now + timedelta(days=2)).date()
    tasks_due = (
        db.query(MaintenanceTask)
        .filter(
            MaintenanceTask.status.in_(["open", "assigned", "in_progress"]),
            MaintenanceTask.due_date <= upcoming_limit,
        )
        .all()
    )

    for task in tasks_due:
        asset_name = task.asset.name if task.asset else f"Asset #{task.asset_id}"
        title = f"Maintenance Task Due: {task.title}"
        body = f"Task '{task.title}' (Priority: {task.priority}) for asset '{asset_name}' is due on {task.due_date}."

        # Notify assigned user if present
        if task.assigned_to:
            n = create_notification(
                db=db,
                user_id=task.assigned_to,
                type="maintenance_deadline_approaching",
                title=title,
                body=body,
                entity_type="task",
                entity_id=str(task.task_id),
                severity="high" if task.priority in ("P1", "P2") else "medium",
            )
            if n:
                summary["maintenance_alerts"] += 1
        else:
            # Notify maintenance engineers
            created = notify_roles(
                db=db,
                type="maintenance_deadline_approaching",
                title=title,
                body=body,
                entity_type="task",
                entity_id=str(task.task_id),
                severity="medium",
                extra_roles=["maintenance_engineer"],
            )
            summary["maintenance_alerts"] += len(created)

    # 2. Overdue asset inspections
    overdue_assets = (
        db.query(InfrastructureAsset)
        .filter(
            InfrastructureAsset.next_inspection_due != None,
            InfrastructureAsset.next_inspection_due <= now.date(),
        )
        .all()
    )

    for asset in overdue_assets:
        title = f"Inspection Overdue: {asset.name}"
        body = f"Asset '{asset.name}' was due for scheduled inspection on {asset.next_inspection_due}. No completed inspection recorded."
        created = notify_roles(
            db=db,
            type="inspection_assigned",
            title=title,
            body=body,
            entity_type="asset",
            entity_id=str(asset.asset_id),
            severity="medium",
            extra_roles=["civil_engineer", "manager", "admin"],
        )
        summary["overdue_inspections"] += len(created)

    return summary
