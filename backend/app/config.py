from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Path to the backend root directory where .env is stored
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # PostgreSQL connection string (defaults to psycopg2 driver)
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/infrascan_db"

    # Environment
    ENV: str = "development"

    # Application secret key
    SECRET_KEY: str = "dev_secret_key_change_me"

    # Authentication & Session configuration
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_MIN_LENGTH: int = 10
    LOCKOUT_ATTEMPTS: int = 5
    LOCKOUT_WINDOW_MINUTES: int = 15
    REGISTRATION_ENABLED: bool = True

    # Google OAuth2 / OpenID Connect (Optional)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    OAUTH_AUTO_CREATE: bool = False

    # Storage configuration
    STORAGE_BACKEND: str = "local"  # "local" or "s3"
    STORAGE_DIR: str = "storage"
    UPLOAD_DIR: str = "storage/uploads"
    PROCESSED_DIR: str = "storage/processed"
    MAX_UPLOAD_SIZE_MB: int = 20
    MIN_IMAGE_WIDTH: int = 640
    MIN_IMAGE_HEIGHT: int = 480

    # S3 / MinIO Object Storage (when STORAGE_BACKEND="s3")
    S3_BUCKET: str = "infrascan"
    S3_ENDPOINT_URL: Optional[str] = None
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    S3_REGION: str = "us-east-1"

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

    # AI Model & Analysis Configuration
    AUTO_ANALYZE: bool = True
    ML_MODELS_DIR: str = "../ml"
    YOLO_WEIGHTS: str = "../ml/detection/yolov8s_rdd2022/weights/best.pt"
    SEG_WEIGHTS: str = "../ml/models/segmentation/unetplusplus_crack500/best.pth"
    SEG_THRESHOLD: float = 0.40
    YOLO_CONF: float = 0.25
    MAX_SIDE: int = 1280
    MASK_DIR: str = "storage/masks"
    EXPLAIN_DIR: str = "storage/explanations"
    REPORT_DIR: str = "storage/reports"
    DETECTION_MODELS_CONFIG: Optional[List[Dict[str, Any]]] = None

    # SMTP / Email Notifications
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "notifications@infrascan.local"
    SMTP_TLS: bool = False
    EMAIL_ENABLED: bool = True

    # Multi-Detector Selection & CODEBRIM Defect Detector
    RUN_ALL_DETECTORS: bool = False
    CODEBRIM_WEIGHTS: str = "../ml/models/detection_codebrim/A2_rtdetr_l/weights/best.pt"
    CODEBRIM_REGISTRY: str = "../ml/models/detection_codebrim/model_registry.json"
    CODEBRIM_CONF: Optional[float] = None
    CODEBRIM_IMGSZ: int = 960

    @property
    def storage_path(self) -> Path:
        """Resolved absolute path to the base storage directory."""
        p = Path(self.STORAGE_DIR)
        if not p.is_absolute():
            return BASE_DIR / p
        return p

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

    @property
    def mask_path(self) -> Path:
        """Resolved absolute path to the mask storage directory."""
        p = Path(self.MASK_DIR)
        if not p.is_absolute():
            return BASE_DIR / p
        return p

    @property
    def explain_path(self) -> Path:
        """Resolved absolute path to the explanations storage directory."""
        p = Path(self.EXPLAIN_DIR)
        if not p.is_absolute():
            return BASE_DIR / p
        return p

    @property
    def report_path(self) -> Path:
        """Resolved absolute path to the reports storage directory."""
        p = Path(self.REPORT_DIR)
        if not p.is_absolute():
            return BASE_DIR / p
        return p

    @property
    def ml_models_path(self) -> Path:
        """Resolved absolute path to the ML models directory."""
        p = Path(self.ML_MODELS_DIR)
        if not p.is_absolute():
            return BASE_DIR / p
        return p

    def get_segmentation_threshold(self) -> float:
        """Read optimal threshold from run_card.json next to SEG_WEIGHTS if present; default SEG_THRESHOLD."""
        seg_w_path = Path(self.SEG_WEIGHTS)
        if not seg_w_path.is_absolute():
            seg_w_path = BASE_DIR / seg_w_path

        run_card = seg_w_path.parent / "run_card.json"
        if run_card.exists():
            try:
                import json
                with open(run_card, "r", encoding="utf-8") as f:
                    data = json.load(f)
                opt_thresh = (
                    data.get("best_validation_results", {}).get("optimal_threshold")
                    or data.get("threshold")
                )
                if opt_thresh is not None:
                    return float(opt_thresh)
            except Exception:
                pass
        return float(self.SEG_THRESHOLD)

    def get_detection_models(self) -> List[Dict[str, Any]]:
        """Return configured detection models list.
        Defaults:
        - yolov8s_rdd2022: road detector
        - A2_rtdetr_l: CODEBRIM detector
        """
        if self.DETECTION_MODELS_CONFIG:
            return self.DETECTION_MODELS_CONFIG

        codebrim_conf = self.CODEBRIM_CONF
        if codebrim_conf is None:
            reg_candidates = [
                self.ml_models_path / "models" / "detection_codebrim" / "model_registry.json",
                BASE_DIR.parent / "ml" / "models" / "detection_codebrim" / "model_registry.json",
                Path(self.CODEBRIM_REGISTRY),
            ]
            for rc in reg_candidates:
                p = rc if rc.is_absolute() else (BASE_DIR / rc)
                if p.exists():
                    try:
                        import json
                        with open(p, "r", encoding="utf-8") as f:
                            d = json.load(f)
                        c = d.get("chosen_confidence")
                        if c is not None:
                            codebrim_conf = float(c)
                            break
                    except Exception:
                        pass
        if codebrim_conf is None:
            codebrim_conf = self.YOLO_CONF

        return [
            {
                "name": "yolov8s_rdd2022",
                "model_id": "yolov8s_rdd2022",
                "model_name": "YOLOv8s RDD2022 Road Damage Detector",
                "weights_path": self.YOLO_WEIGHTS,
                "class_names": {
                    0: "D00 longitudinal crack",
                    1: "D10 transverse crack",
                    2: "D20 alligator crack",
                    3: "D40 pothole",
                },
                "conf": self.YOLO_CONF,
                "confidence": self.YOLO_CONF,
                "imgsz": 640,
                "model_class": "yolo",
                "applicable_asset_types": ["road"],
                "applicable_material_types": ["asphalt"],
                "domain_note": "trained on road damage images (RDD2022)",
            },
            {
                "name": "A2_rtdetr_l",
                "model_id": "A2_rtdetr_l",
                "model_name": "CODEBRIM Defect Detector (RT-DETR-L)",
                "weights_path": self.CODEBRIM_WEIGHTS,
                "class_names": {
                    0: "crack",
                    1: "spallation",
                    2: "exposed_bars",
                    3: "efflorescence",
                    4: "corrosion_stain",
                },
                "conf": codebrim_conf,
                "confidence": codebrim_conf,
                "imgsz": self.CODEBRIM_IMGSZ,
                "model_class": "rtdetr",
                "applicable_asset_types": [
                    "bridge",
                    "building",
                    "tunnel",
                    "dam",
                    "concrete_structure",
                    "retaining_wall",
                    "industrial",
                ],
                "applicable_material_types": ["concrete", "steel", "masonry"],
                "domain_note": "trained on bridge defect images (CODEBRIM); not validated for other structures",
            },
        ]

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.ENV == "production":
            if self.SECRET_KEY == "dev_secret_key_change_me" or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "Production mode requires SECRET_KEY to be at least 32 characters and not the default dev key."
                )
        return self

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Instantiate settings for use across the application
settings = Settings()
