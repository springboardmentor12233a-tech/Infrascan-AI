# InfraScan backend

## Run locally

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The default database is `sqlite:///./infrascan.db`. Set `DATABASE_URL` to a PostgreSQL/PostGIS SQLAlchemy URL for deployment. Uploaded originals and processed derivatives are stored in `backend/media` (override with `INFRASCAN_MEDIA_DIR`).

Run the smoke test with `pytest -q`. API docs are available at `http://localhost:8000/docs`.
