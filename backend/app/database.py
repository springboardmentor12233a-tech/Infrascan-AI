"""
database.py – SQLAlchemy engine + session factory.

Supports both PostgreSQL and SQLite via DATABASE_URL.
SQLite needs the connect_args tweak so it works in multi-threaded FastAPI.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

# ── Engine setup ─────────────────────────────────────────────────────────────
# SQLite needs check_same_thread=False because FastAPI runs requests on
# multiple threads. PostgreSQL does not need this argument.
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG,   # prints SQL to console when DEBUG=true – great for learning
)

# ── Session factory ───────────────────────────────────────────────────────────
# Each request gets its own session, opened and closed in the dependency below.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Base class for all models ─────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── FastAPI dependency ────────────────────────────────────────────────────────
def get_db():
    """
    Yields a database session and closes it when the request is done.
    Usage in a router:  db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
