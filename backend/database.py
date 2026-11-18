from pathlib import Path
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    DateTime, inspect, text
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

DATABASE_PATH = Path(__file__).resolve().parent / "infrascan.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


class InfrastructureAsset(Base):
    __tablename__ = "infrastructure_assets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    asset_type = Column(String(50), nullable=False)
    location = Column(String(200), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

class AssessmentResult(Base):
    __tablename__ = "assessment_results"

    id = Column(Integer, primary_key=True, index=True)
    image_name = Column(String(255), nullable=False)
    prediction = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Milestone 3 fields
    asset_id = Column(Integer, nullable=True, index=True)
    model_name = Column(String(100), nullable=True)
    severity = Column(String(50), nullable=True)
    maintenance_priority = Column(String(50), nullable=True)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)


Base.metadata.create_all(bind=engine)

# Safely add missing columns to an existing SQLite database
existing_columns = {
    column["name"]
    for column in inspect(engine).get_columns("assessment_results")
}

new_columns = {
    "asset_id": "INTEGER",
    "model_name": "VARCHAR(100)",
    "severity": "VARCHAR(50)",
    "maintenance_priority": "VARCHAR(50)",
}

with engine.begin() as connection:
    for column_name, column_type in new_columns.items():
        if column_name not in existing_columns:
            connection.execute(
                text(
                    f"ALTER TABLE assessment_results "
                    f"ADD COLUMN {column_name} {column_type}"
                )
            )



# Safely add latitude and longitude to existing infrastructure assets
asset_columns = {
    column["name"]
    for column in inspect(engine).get_columns("infrastructure_assets")
}

asset_new_columns = {
    "latitude": "FLOAT",
    "longitude": "FLOAT",
}

with engine.begin() as connection:
    for column_name, column_type in asset_new_columns.items():
        if column_name not in asset_columns:
            connection.execute(
                text(
                    f"ALTER TABLE infrastructure_assets "
                    f"ADD COLUMN {column_name} {column_type}"
                )
            )