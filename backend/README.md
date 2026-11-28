# InfraScan Backend

FastAPI backend for the InfraScan AI-powered infrastructure inspection platform.

## Stack

| Component | Technology |
|---|---|
| Framework | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.0 |
| Validation | Pydantic v2 |
| Auth | JWT (python-jose) + bcrypt |
| Database (dev) | SQLite (file: `infrascan_dev.db`) |
| Database (prod) | PostgreSQL via psycopg |
| Background tasks | Celery + Redis (optional) |
| Image storage | Local filesystem (`./storage/`) |

---

## Setup

### 1. Install dependencies

```powershell
cd backend
pip install -r requirements.txt
```

> **Windows note:** If `psycopg[binary]` fails, it can be safely ignored for SQLite-only dev.
> The app falls back to SQLite automatically.

### 2. Create `.env`

Copy the example and adjust if needed:

```powershell
copy .env.example .env
```

Default dev `.env` uses SQLite — no PostgreSQL installation required.

### 3. Seed demonstration data

```powershell
python scripts/seed.py
```

This creates 3 users, 3 assets, and 2 inspections with clearly labeled `[DEMO]` prefixes.

**Demo credentials:**

| Role | Email | Password |
|---|---|---|
| Admin | admin@infrascan.io | adminpass123 |
| Engineer | elena.vance@infrascan.io | password123 |
| Inspector | marcus.torres@infrascan.io | password123 |

---

## Start the server

```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

API is available at `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

---

## Run tests

```powershell
cd backend
pytest tests/ -v
```

Tests use the same SQLite database in dev mode (no separate test DB needed).

---

## API Endpoints

### Authentication
| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Create account → returns TokenPair |
| POST | `/api/v1/auth/login` | Login → returns TokenPair |
| GET | `/api/v1/auth/me` | Get current user (requires Bearer token) |

### Infrastructure Assets
| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/assets` | Create asset |
| GET | `/api/v1/assets` | List assets (filter by `q`, `infrastructure_type`) |
| GET | `/api/v1/assets/{id}` | Get asset |
| PATCH | `/api/v1/assets/{id}` | Update asset |
| DELETE | `/api/v1/assets/{id}` | Archive asset (soft delete) |

### Inspections
| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/inspections` | Create inspection |
| GET | `/api/v1/inspections` | List (filter by `asset_id`) |
| GET | `/api/v1/inspections/{id}` | Get inspection |
| PATCH | `/api/v1/inspections/{id}` | Update inspection status/notes |

### Images
| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/images/upload` | Upload image file (multipart) |
| GET | `/api/v1/images` | List images |
| GET | `/api/v1/images/{id}/file` | Serve image file |

### AI Analysis
| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/analysis` | Queue analysis job |
| GET | `/api/v1/analysis` | List jobs |
| GET | `/api/v1/analysis/{id}/status` | Poll job status |
| POST | `/api/v1/findings/{id}/reviews` | Submit engineer review |

---

## Known Limitations

- **Docker not available** on this machine — Docker Compose cannot be used. Run uvicorn directly.
- **No Redis/Celery** in dev — analysis jobs are created but not actually processed (placeholder worker).
- **SQLite in dev** — switches to PostgreSQL by setting `DATABASE_URL` in `.env`.
- **Bearer tokens in localStorage** — not HttpOnly cookies. Acceptable for dev; use secure cookies in production.
- **No Alembic migrations** — `Base.metadata.create_all()` runs on startup for dev convenience.
- **No real ML inference** — `process_analysis` Celery task is a placeholder. Connect PyTorch models when available.
- **Missing endpoints** (future work):
  - `GET /api/v1/assets/{id}/progression` (damage progression over time)
  - `GET /api/v1/analysis/{id}` full result detail
  - `POST /api/v1/reports`, `GET /api/v1/reports`
  - `GET /api/v1/users`, `PATCH /api/v1/users/{id}`

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | (dev default) | JWT signing secret — **change in production** |
| `DATABASE_URL` | `sqlite:///./infrascan_dev.db` | Database connection string |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Comma-separated allowed origins |
| `STORAGE_DIR` | `./storage` | Directory for uploaded image files |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT access token lifetime |
| `MAX_UPLOAD_SIZE_MB` | `25` | Maximum image upload size |

