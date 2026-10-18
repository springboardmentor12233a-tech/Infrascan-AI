"""
config.py – central place for all app settings.

Pydantic-settings reads these from environment variables or from a .env file
automatically. Changing a value here is as simple as updating .env.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME: str = "InfraScan"
    DEBUG: bool = False

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./infrascan.db"  # SQLite fallback

    # ── JWT ───────────────────────────────────────────────────────────────────
    SECRET_KEY: str = "changeme"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── Uploads ───────────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 20
    MIN_IMAGE_WIDTH: int = 64
    MIN_IMAGE_HEIGHT: int = 64

    # ── Quality thresholds ────────────────────────────────────────────────────
    BLUR_THRESHOLD: float = 100.0
    BRIGHTNESS_THRESHOLD: float = 50.0

    # ── CORS ──────────────────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"

    # ── Google OAuth (stub) ───────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Pydantic-settings config: look for a .env file in the same dir as this file
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Single shared instance – import this everywhere
settings = Settings()
