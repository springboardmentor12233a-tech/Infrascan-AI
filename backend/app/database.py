from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# Ensure psycopg2 driver is specified for PostgreSQL
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# Engine keyword arguments with connection pool tuning for production scalability
engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
}
if "sqlite" not in db_url:
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 3600,
    })

engine = create_engine(db_url, **engine_kwargs)

# SessionLocal class for instantiating database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for database models
Base = declarative_base()


# Dependency to yield a database session per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

