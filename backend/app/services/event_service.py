import asyncio
import json
import logging
import secrets
import select
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set
from sqlalchemy import delete, func, text
from sqlalchemy.orm import Session
from sqlalchemy import event as sqla_event

from app.config import settings
from app.database import SessionLocal, engine
from app.models.event import Event, EventTicket
from app.models.user import User

logger = logging.getLogger(__name__)

# Maximum concurrent streams per user
MAX_CONCURRENT_STREAMS_PER_USER = 5

# Global in-memory subscriber management
class EventBroker:
    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()
        self._lock = threading.Lock()
        self._active_streams_by_user: Dict[int, int] = {}
        self._listener_running = False

    def add_subscriber(self, queue: asyncio.Queue):
        with self._lock:
            self._subscribers.add(queue)

    def remove_subscriber(self, queue: asyncio.Queue):
        with self._lock:
            self._subscribers.discard(queue)

    def broadcast(self, event_dict: dict):
        with self._lock:
            subscribers_snapshot = list(self._subscribers)
        for q in subscribers_snapshot:
            try:
                q.put_nowait(event_dict)
            except Exception:
                pass

    def acquire_stream(self, user_id: int) -> bool:
        with self._lock:
            current = self._active_streams_by_user.get(user_id, 0)
            if current >= MAX_CONCURRENT_STREAMS_PER_USER:
                return False
            self._active_streams_by_user[user_id] = current + 1
            return True

    def release_stream(self, user_id: int):
        with self._lock:
            current = self._active_streams_by_user.get(user_id, 0)
            if current > 1:
                self._active_streams_by_user[user_id] = current - 1
            else:
                self._active_streams_by_user.pop(user_id, None)

broker = EventBroker()


def can_user_see(user: User, event_item: Any) -> bool:
    """
    Evaluate whether a user has permission to receive or view a specific event.
    Accepts an Event model instance or a dictionary.
    """
    if isinstance(event_item, dict):
        event_type = event_item.get("type", "")
        audience = event_item.get("audience") or {}
        payload = event_item.get("payload") or {}
    else:
        event_type = event_item.type
        audience = event_item.audience_json or {}
        payload = event_item.payload_json or {}

    # 1. Direct user targeted
    user_ids = audience.get("user_ids")
    if user_ids and user.user_id in user_ids:
        return True

    # 2. Global audience
    if audience.get("all") is True:
        return True

    # 3. Role filtering
    allowed_roles = audience.get("roles")
    if allowed_roles and user.role not in allowed_roles:
        return False

    # 4. Administrators and Managers can observe operational events by default
    if user.role in ("admin", "manager"):
        return True

    # 5. Inspector-specific scoping
    if user.role == "inspector":
        inspector_id = audience.get("inspector_id") or payload.get("inspector_id")
        if inspector_id is not None and int(inspector_id) != user.user_id:
            return False

    # 6. Maintenance engineer scoping: never see unconfirmed/provisional severity
    if user.role == "maintenance_engineer":
        if "severity" in event_type and not payload.get("is_confirmed", False) and event_type != "severity.confirmed":
            return False
        assigned_to = audience.get("assigned_to") or payload.get("assigned_to")
        if assigned_to is not None and int(assigned_to) != user.user_id and event_type.startswith("task."):
            return False

    return True


def publish(
    db: Session,
    event_type: str,
    entity_type: str,
    entity_id: Any,
    audience: dict,
    payload: dict,
) -> Event:
    """
    Publish an event transactionally.
    Writes event row and registers an after-commit hook to dispatch notifications.
    If the transaction rolls back, nothing is published.
    """
    event_obj = Event(
        type=event_type,
        entity_type=entity_type,
        entity_id=str(entity_id),
        audience_json=audience,
        payload_json=payload,
    )
    db.add(event_obj)
    db.flush()

    event_id = event_obj.event_id
    event_dict = event_obj.to_dict()

    # Register after_commit hook
    @sqla_event.listens_for(db, "after_commit", once=True)
    def notify_after_commit(session):
        # 1. In-memory broadcast (for active websockets / SSE within this instance)
        broker.broadcast(event_dict)

        # 2. PostgreSQL LISTEN/NOTIFY for cross-process scaling
        try:
            if engine.dialect.name == "postgresql":
                with engine.connect() as conn:
                    conn.execute(
                        text("SELECT pg_notify('infrascan_events', :payload)"),
                        {"payload": str(event_id)},
                    )
                    conn.commit()
        except Exception as ex:
            logger.warning("pg_notify error: %s", ex)

    return event_obj


def create_event_ticket(db: Session, user: User, expiry_seconds: int = 30) -> str:
    """Generate a single-use cryptographic ticket with 30s expiry."""
    ticket = secrets.token_hex(32)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=expiry_seconds)

    record = EventTicket(
        ticket_id=ticket,
        user_id=user.user_id,
        expires_at=expires_at,
        created_at=now,
    )
    db.add(record)
    db.commit()
    return ticket


def validate_and_consume_ticket(db: Session, ticket_id: str) -> Optional[User]:
    """Validate ticket, ensure not expired, mark as used, and return the User."""
    now = datetime.now(timezone.utc)
    record = db.query(EventTicket).filter(EventTicket.ticket_id == ticket_id).first()
    if not record:
        return None

    if record.used_at is not None:
        return None  # Replay attack prevention: single use only

    record_expires = record.expires_at
    if record_expires.tzinfo is None:
        record_expires = record_expires.replace(tzinfo=timezone.utc)

    if record_expires < now:
        return None  # Expired

    # Mark as used atomically
    record.used_at = now
    db.commit()
    return record.user


def get_events_since(
    db: Session,
    since_event_id: int,
    user: User,
    max_age_minutes: int = 10,
    limit: int = 100,
) -> List[dict]:
    """Replay missed events from Last-Event-ID up to max_age_minutes ago."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=max_age_minutes)
    dialect = getattr(getattr(db, "bind", None), "dialect", None)
    if dialect and dialect.name == "sqlite":
        cutoff = cutoff.replace(tzinfo=None)

    query = (
        db.query(Event)
        .filter(Event.event_id > since_event_id, Event.created_at >= cutoff)
        .order_by(Event.event_id.asc())
        .limit(limit)
    )

    results = []
    for evt in query.all():
        if can_user_see(user, evt):
            results.append(evt.to_dict())
    return results


def purge_old_events(db: Session, max_age_days: int = 7) -> int:
    """Purge events older than max_age_days and expired tickets."""
    now = datetime.now(timezone.utc)
    event_cutoff = now - timedelta(days=max_age_days)
    ticket_cutoff = now - timedelta(hours=1)

    dialect = getattr(getattr(db, "bind", None), "dialect", None)
    if dialect and dialect.name == "sqlite":
        event_cutoff = event_cutoff.replace(tzinfo=None)
        ticket_cutoff = ticket_cutoff.replace(tzinfo=None)

    # Delete old events
    stmt_events = delete(Event).where(Event.created_at < event_cutoff)
    res_events = db.execute(stmt_events)

    # Delete old tickets
    stmt_tickets = delete(EventTicket).where(EventTicket.expires_at < ticket_cutoff)
    db.execute(stmt_tickets)

    db.commit()
    return res_events.rowcount or 0


# PostgreSQL Background Listener for multi-process environments
def start_pg_listener():
    """Background daemon thread listening on PostgreSQL 'infrascan_events' channel."""
    if broker._listener_running or engine.dialect.name != "postgresql":
        return

    def listener_worker():
        broker._listener_running = True
        import psycopg2
        import psycopg2.extensions
        from urllib.parse import urlparse

        db_url = str(settings.DATABASE_URL)
        if db_url.startswith("postgresql+psycopg2://"):
            db_url = db_url.replace("postgresql+psycopg2://", "postgresql://", 1)

        try:
            parsed = urlparse(db_url)
            conn = psycopg2.connect(
                dbname=parsed.path.lstrip("/"),
                user=parsed.username,
                password=parsed.password,
                host=parsed.hostname or "localhost",
                port=parsed.port or 5432,
            )
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            curs = conn.cursor()
            curs.execute("LISTEN infrascan_events;")
            logger.info("PostgreSQL LISTEN on channel 'infrascan_events' active.")

            while broker._listener_running:
                if select.select([conn], [], [], 5) == ([], [], []):
                    continue
                conn.poll()
                while conn.notifies:
                    notify = conn.notifies.pop(0)
                    try:
                        event_id = int(notify.payload)
                        with SessionLocal() as db:
                            evt = db.query(Event).filter(Event.event_id == event_id).first()
                            if evt:
                                broker.broadcast(evt.to_dict())
                    except Exception as err:
                        logger.error("Error dispatching pg_notify event: %s", err)
        except Exception as e:
            logger.warning("PG listener stopped: %s", e)
        finally:
            broker._listener_running = False

    t = threading.Thread(target=listener_worker, daemon=True, name="PGEventListener")
    t.start()
