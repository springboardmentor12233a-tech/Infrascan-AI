# InfraScan Real-Time Engine Architecture & Design (`realtime_design.md`)

## 1. Architectural Strategy: PostgreSQL LISTEN/NOTIFY + SSE

InfraScan achieves instant cross-role collaboration using a **zero-Redis, database-backed Server-Sent Events (SSE)** architecture powered by native PostgreSQL `LISTEN/NOTIFY`.

```
[ FastAPI Mutation Endpoint ]
              │
              ▼
   (SQLAlchemy Transaction)
              │
    ┌─────────┴─────────┐
    ▼                   ▼
 [ Commit DB Rows ]  [ Insert `events` Row ]
    │                   │
    └─────────┬─────────┘
              ▼
    (After-Commit Hook)
              │
              ▼
    pg_notify('infrascan_events', event_id)
              │
    ┌─────────┴─────────┐
    ▼                   ▼
[ Worker 1 (SSE) ]  [ Worker 2 (SSE) ]
    │                   │
    ▼                   ▼
`can_user_see()`    `can_user_see()`
    │                   │
    ▼                   ▼
(Audience Match)    (Audience Match)
    │                   │
    ▼                   ▼
Browser 1 (SSE)     Browser 2 (SSE)
```

---

## 2. Core Components

### 2.1 The `events` and `event_tickets` Schema
- **`events` Table**:
  - `event_id`: BigSerial Primary Key (monotonically increasing sequence).
  - `type`: String event identifier (e.g. `inspection.assigned`, `severity.confirmed`).
  - `entity_type`: String (e.g. `inspection`, `asset`, `task`, `user`).
  - `entity_id`: String identifier of target entity.
  - `audience_json`: JSON structure defining target recipients:
    `{"roles": ["admin", "manager"], "user_ids": [12], "all": false}`.
  - `payload_json`: Sanitized, non-sensitive payload dictionary.
  - `created_at`: UTC timestamp.
- **`event_tickets` Table**:
  - `ticket`: 64-character hex token (32 bytes cryptographically secure random).
  - `user_id`: Associated authenticated user ID.
  - `expires_at`: Strict 30-second expiry window.
  - `used_at`: Timestamp marking single-use consumption.

### 2.2 Transactional Publication
The `publish(db, ...)` helper registers an `after_commit` event listener on the active SQLAlchemy session:
- Guarantees the originating business transaction (e.g., creating an inspection, confirming severity) has **fully committed to disk** before any event is published.
- Issues `pg_notify('infrascan_events', str(event.event_id))` across the shared PostgreSQL channel.
- If running under SQLite during isolated unit tests, broadcasts directly to the process's in-memory broker.

### 2.3 Ticket Authentication Handshake
Browsers cannot attach custom HTTP authorization headers to standard `EventSource` connections. InfraScan resolves this cleanly:
1. Client makes an authenticated `POST /events/ticket` request carrying their `Bearer <access_token>`.
2. Backend generates a cryptographic single-use ticket valid for 30 seconds.
3. Client initiates the stream with `GET /events/stream?ticket=<ticket>`.
4. Backend validates ticket, marks it consumed (`used_at = now()`), and begins the SSE event pump.

### 2.4 Multi-Worker Synchronization & Audience Filtering
- Every Uvicorn worker process maintains a lightweight background listener thread connected to the PostgreSQL `infrascan_events` channel.
- When an event arrives, all workers fetch the event by `event_id`.
- Each worker filters the event using the single authoritative permission check: `can_user_see(user, event)`:
  - If `audience.all == true`, all authenticated users receive the event.
  - If `audience.user_ids` contains the user's ID, the user receives it.
  - If `audience.roles` contains the user's role, the user receives it.
  - Otherwise, the event is silently suppressed, guaranteeing strict cross-tenant isolation.

### 2.5 Reconnection & Last-Event-ID Replay
- When a client experiences temporary network interruption, it reconnects supplying the standard `Last-Event-ID` header (or query param).
- Backend queries `get_events_since(last_id, user, lookback_window=600)` to replay all missed visible events from the past 10 minutes in strict sequence before resuming live transmission.

### 2.6 Resilience: Heartbeats & Polling Fallback
- **Heartbeats**: Every 15 seconds, the backend emits `:heartbeat` SSE comment frames to keep intermediate proxies, firewalls, and load balancers from terminating idle HTTP connections.
- **Connection Limits**: Backend restricts each user to at most 5 concurrent active SSE streams.
- **Automatic Polling Fallback**: If SSE connection fails 3 consecutive times, the frontend hook (`useLiveEvents.ts`) automatically switches to polling `GET /events/poll?since_id=...` every 15 seconds, updating the live status chip from "Reconnecting" to "Polling".

### 2.7 Retention & Maintenance
- Events older than 7 days are automatically purged by `purge_old_events(db, retention_days=7)` executed by the background maintenance worker.
