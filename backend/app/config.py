from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Path to the backend root directory where .env is stored
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # PostgreSQL connection string (defaults to psycopg2 driver)
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/infrascan_db"

    # Application secret key
    SECRET_KEY: str = "dev_secret_key_change_me"

    # Storage configuration
    UPLOAD_DIR: str = "storage/uploads"
    PROCESSED_DIR: str = "storage/processed"
    MAX_UPLOAD_SIZE_MB: int = 20
    MIN_IMAGE_WIDTH: int = 640
    MIN_IMAGE_HEIGHT: int = 480

    # Image quality check thresholds (tuned in config)
    BLUR_THRESHOLD: float = 100.0
    BRIGHTNESS_MIN: float = 50.0
    BRIGHTNESS_MAX: float = 220.0

    # Preprocessing pipeline settings
    MODEL_INPUT_SIZE: int = 256
    NORMALIZE_MODE: str = "zero_one"  # "zero_one" or "imagenet"
    ENABLE_CONTRAST: bool = True
    ENABLE_DENOISE: bool = False
    ENABLE_SHARPEN: bool = False
    CLAHE_CLIP_LIMIT: float = 2.0
    CLAHE_TILE_GRID: int = 8

    @property
    def upload_path(self) -> Path:
        """Resolved absolute path to the uploads directory."""
        p = Path(self.UPLOAD_DIR)
        if not p.is_absolute():
            return BASE_DIR / p
        return p

    @property
    def processed_path(self) -> Path:
        """Resolved absolute path to the processed images directory."""
        p = Path(self.PROCESSED_DIR)
        if not p.is_absolute():
            return BASE_DIR / p
        return p

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Instantiate settings for use across the application
settings = Settings()
