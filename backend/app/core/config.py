import json
from typing import List, Union, Any
from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # General
    PROJECT_NAME: str = "DocForge"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    @field_validator("TRUSTED_PROXIES", "CORS_ORIGINS", mode="before", check_fields=False)
    @classmethod
    def parse_string_lists(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    return json.loads(v_stripped)
                except Exception:
                    pass
            return [item.strip() for item in v_stripped.split(",") if item.strip()]
        return v

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "docforge"
    POSTGRES_PASSWORD: str = "docforge_dev"
    POSTGRES_DB: str = "docforge"
    DATABASE_URL_OVERRIDE: Union[str, None] = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        if self.DATABASE_URL_OVERRIDE:
            return self.DATABASE_URL_OVERRIDE
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Object Storage (MinIO / AWS S3 / Cloudflare R2)
    STORAGE_PROVIDER: str = "minio"  # "minio" | "s3" | "r2"
    STORAGE_ENDPOINT: str = "http://localhost:9000"
    STORAGE_ACCESS_KEY: str = "minioadmin"
    STORAGE_SECRET_KEY: str = "minioadmin"
    STORAGE_BUCKET_INPUTS: str = "docforge-inputs"
    STORAGE_BUCKET_OUTPUTS: str = "docforge-outputs"
    STORAGE_USE_SSL: bool = False
    STORAGE_REGION: str = "us-east-1"
    STORAGE_PUBLIC_DOMAIN: Union[str, None] = None  # e.g., "https://pub-r2.docforge.com"
    STORAGE_PRESIGNED_ENDPOINT_OVERRIDE: Union[str, None] = None  # e.g., "http://localhost:9000"

    # Monitoring & Telemetry (Sentry)
    SENTRY_DSN: Union[str, None] = None
    SENTRY_ENVIRONMENT: str = "production"
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    SENTRY_PROFILES_SAMPLE_RATE: float = 0.0

    # Worker Health
    CELERY_WORKER_PING_TIMEOUT: float = 2.0

    # Job Limits
    MAX_FILE_SIZE_MB: int = 50
    MAX_FILES_PER_JOB: int = 20
    DEFAULT_JOB_TTL_SECONDS: int = 7200  # 2 hours

    # PDF to JPG Specific Resource Limits
    PDF_TO_JPG_MAX_FILE_SIZE_MB: int = 50
    PDF_TO_JPG_MAX_PAGES_DEFAULT: int = 100        # Max pages for <= 150 DPI
    PDF_TO_JPG_MAX_PAGES_300_DPI: int = 50         # Max pages for > 150 DPI (300 DPI high resolution)
    PDF_TO_JPG_MAX_RENDER_DIMENSION: int = 8000    # Max width or height in pixels of rendered page
    PDF_TO_JPG_MAX_RENDER_PIXELS: int = 36_000_000 # Max total pixels (e.g. ~36 MP) per page bitmap
    PDF_TO_JPG_MAX_AGGREGATE_OUTPUT_MB: int = 250  # Max aggregate output JPEG bytes / ZIP archive size in MB

    # JPG to PDF Specific Resource Limits
    JPG_TO_PDF_MAX_FILE_SIZE_MB: int = 25
    JPG_TO_PDF_MAX_FILES: int = 50
    JPG_TO_PDF_MAX_IMAGE_DIMENSION: int = 10000
    JPG_TO_PDF_MAX_TOTAL_PIXELS: int = 150_000_000
    JPG_TO_PDF_MAX_OUTPUT_PDF_MB: int = 100

    # Aggregate Upload Limits
    MAX_AGGREGATE_JOB_SIZE_MB: int = 250

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_JOB_CREATION_LIMIT: int = 20  # requests per window
    RATE_LIMIT_JOB_CREATION_WINDOW: int = 60  # seconds
    RATE_LIMIT_UPLOAD_LIMIT: int = 60  # requests per window
    RATE_LIMIT_UPLOAD_WINDOW: int = 60  # seconds
    RATE_LIMIT_GENERAL_LIMIT: int = 120  # requests per window
    RATE_LIMIT_GENERAL_WINDOW: int = 60  # seconds
    TRUSTED_PROXIES: Union[List[str], str] = ["127.0.0.1", "::1", "localhost"]

    @field_validator("TRUSTED_PROXIES")
    @classmethod
    def normalize_trusted_proxies(cls, v: Union[List[str], str]) -> List[str]:
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    return json.loads(v_stripped)
                except Exception:
                    pass
            return [item.strip() for item in v_stripped.split(",") if item.strip()]
        return v

    # Antivirus / ClamAV Scanner
    CLAMAV_ENABLED: bool = False
    CLAMAV_HOST: str = "localhost"
    CLAMAV_PORT: int = 3310
    CLAMAV_TIMEOUT_SECONDS: float = 10.0
    CLAMAV_FAIL_CLOSED: bool = True

    # Security Headers
    ENABLE_HSTS: bool = False

    # Logging
    LOG_LEVEL: str = "INFO"

    # SSE Streaming
    SSE_HEARTBEAT_INTERVAL: float = 15.0


settings = Settings()
