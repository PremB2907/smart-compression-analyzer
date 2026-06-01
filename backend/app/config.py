from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_SECRET_PLACEHOLDER = "change-me-in-production-use-openssl-rand-hex-32"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SecureArchive AI"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"
    log_level: str = "INFO"
    secret_key: str = _INSECURE_SECRET_PLACEHOLDER
    access_token_expire_minutes: int = 480
    algorithm: str = "HS256"
    external_command_timeout_sec: int = 120

    celery_worker_concurrency: int = 1
    celery_task_time_limit_sec: int = 600
    # When true tasks run synchronously in the web process (useful for local dev without Redis)
    celery_task_always_eager: bool = False

    # Default to a lightweight local SQLite DB for developer convenience.
    # Production should set `DATABASE_URL` explicitly (Postgres, etc.).
    database_url: str = "sqlite:///./dev.db"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "securearchive"
    minio_secure: bool = False

    max_upload_size_mb: int = 50
    max_files_per_batch: int = 10
    allowed_extensions: str = ".png,.jpg,.jpeg,.bmp,.tif,.tiff,.pdf"

    reference_width: int = 1000
    reference_height: int = 1414

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_ext_set(self) -> set[str]:
        return {e.strip().lower() for e in self.allowed_extensions.split(",")}

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.is_production:
            if self.secret_key == _INSECURE_SECRET_PLACEHOLDER or len(self.secret_key) < 32:
                raise ValueError(
                    "SECRET_KEY must be set to a random string of at least 32 characters in production"
                )
            if self.minio_secret_key in ("minioadmin", "changeme-local-docker-only"):
                raise ValueError("MINIO_SECRET_KEY must not use default credentials in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
