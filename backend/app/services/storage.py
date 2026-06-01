import logging
import time
from collections.abc import Callable
from io import BytesIO
from pathlib import Path
from typing import TypeVar
from uuid import uuid4

from minio import Minio
from minio.error import S3Error

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

T = TypeVar("T")
_MAX_RETRIES = 3
_RETRY_BASE_DELAY_SEC = 0.5


class StorageService:
    def __init__(self) -> None:
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.bucket = settings.minio_bucket
        self._ensure_bucket()

    def _retry_s3(self, operation: str, func: Callable[[], T]) -> T:
        last_exc: S3Error | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                return func()
            except S3Error as exc:
                last_exc = exc
                if attempt >= _MAX_RETRIES:
                    break
                delay = _RETRY_BASE_DELAY_SEC * attempt
                logger.warning(
                    "MinIO %s failed (attempt %s/%s), retrying in %.1fs: %s",
                    operation,
                    attempt,
                    _MAX_RETRIES,
                    delay,
                    exc,
                )
                time.sleep(delay)
        assert last_exc is not None
        logger.error("MinIO %s failed after %s attempts", operation, _MAX_RETRIES)
        raise last_exc

    def _ensure_bucket(self) -> None:
        def _ensure() -> str:
            if self.client.bucket_exists(self.bucket):
                return "exists"
            self.client.make_bucket(self.bucket)
            return "created"

        try:
            status = self._retry_s3("ensure_bucket", _ensure)
            if status == "created":
                logger.info("Created MinIO bucket: %s", self.bucket)
        except S3Error as exc:
            logger.warning("Could not ensure bucket %s exists: %s", self.bucket, exc)

    def upload_file(self, local_path: Path, prefix: str = "uploads") -> str:
        key = f"{prefix}/{uuid4().hex}/{local_path.name}"

        def _put() -> None:
            self.client.fput_object(self.bucket, key, str(local_path))

        self._retry_s3("upload_file", _put)
        return key

    def upload_bytes(self, data: bytes, filename: str, prefix: str = "artifacts") -> str:
        key = f"{prefix}/{uuid4().hex}/{filename}"

        def _put() -> None:
            self.client.put_object(self.bucket, key, BytesIO(data), length=len(data))

        self._retry_s3("upload_bytes", _put)
        return key

    def download_to_path(self, key: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)

        def _get() -> None:
            self.client.fget_object(self.bucket, key, str(dest))

        self._retry_s3("download_to_path", _get)
        return dest

    def get_presigned_url(self, key: str, expires_hours: int = 1) -> str:
        from datetime import timedelta

        return self.client.presigned_get_object(
            self.bucket, key, expires=timedelta(hours=expires_hours)
        )
