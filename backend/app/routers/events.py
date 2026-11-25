import asyncio
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.user import User
from app.services.event_service import (
    broker,
    can_user_see,
    create_event_ticket,
    get_events_since,
    purge_old_events,
    validate_and_consume_ticket,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["Real-Time Events"])


@router.post("/ticket")
def request_stream_ticket(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate a single-use cryptographic ticket with 30s expiry
    for authenticating an SSE EventSource connection.
    """
    ticket = create_event_ticket(db, current_user, expiry_seconds=30)
    return {
        "ticket": ticket,
        "expires_in": 30,
        "user_id": current_user.user_id,
        "role": current_user.role,
    }


@router.get("/stream")
async def stream_live_events(
    request: Request,
    ticket: str = Query(..., description="Single-use ticket generated via POST /events/ticket"),
    last_event_id_header: Optional[str] = Header(None, alias="Last-Event-ID"),
    last_event_id_query: Optional[int] = Query(None, alias="last_event_id"),
    db: Session = Depends(get_db),
):
    """
    Server-Sent Events (SSE) stream endpoint.
    Transmits live system events with audience filtering, 15s heartbeats,
    and automatic Last-Event-ID replay of missed events up to 10 minutes.
    """
    user = validate_and_consume_ticket(db, ticket)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or already consumed ticket.",
        )

    # Enforce maximum concurrent streams per user
    if not broker.acquire_stream(user.user_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Maximum concurrent live streams (5) reached for this account.",
        )

    user_id = user.user_id

    # Resolve last_event_id
    last_id = 0
    if last_event_id_header and last_event_id_header.isdigit():
        last_id = int(last_event_id_header)
    elif last_event_id_query is not None:
        last_id = last_event_id_query

    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        broker.add_subscriber(queue)
        try:
            # 1. Replay missed events from Last-Event-ID if requested
            if last_id > 0:
                missed_events = get_events_since(db, last_id, user, max_age_minutes=10)
                for evt in missed_events:
                    yield f"id: {evt['event_id']}\nevent: {evt['type']}\ndata: {json.dumps(evt)}\n\n"

            # 2. Main SSE streaming loop
            while True:
                # Disconnect check
                if await request.is_disconnected():
                    break

                try:
                    event_data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    if can_user_see(user, event_data):
                        eid = event_data.get("event_id", "")
                        etype = event_data.get("type", "message")
                        yield f"id: {eid}\nevent: {etype}\ndata: {json.dumps(event_data)}\n\n"
                except asyncio.TimeoutError:
                    # 15-second heartbeat keeping connection alive through proxies
                    yield ":heartbeat\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            broker.remove_subscriber(queue)
            broker.release_stream(user_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/poll")
def poll_events(
    since_id: int = Query(0, ge=0, description="Return events strictly greater than this event_id"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    HTTP polling fallback endpoint for clients when SSE / EventSource is unavailable.
    """
    events = get_events_since(db, since_id, current_user, max_age_minutes=10, limit=limit)
    last_id = events[-1]["event_id"] if events else since_id
    return {
        "events": events,
        "last_id": last_id,
        "count": len(events),
    }


@router.delete("/purge", dependencies=[Depends(require_roles("admin"))])
def purge_events(
    max_age_days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """Admin maintenance: purge events older than max_age_days (default: 7 days)."""
    count = purge_old_events(db, max_age_days=max_age_days)
    return {"message": f"Purged {count} events older than {max_age_days} days."}
