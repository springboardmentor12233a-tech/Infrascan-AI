import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_STORAGE = os.environ.get(
    "INFRASCAN_STORAGE_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)
DB_PATH = os.environ.get("INFRASCAN_DB_PATH", os.path.join(BASE_STORAGE, "infrascan.db"))
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
