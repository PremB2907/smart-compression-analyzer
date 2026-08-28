import logging
import shutil
import time
from collections.abc import Callable
from io import BytesIO
from pathlib import Path
from typing import TypeVar
from uuid import uuid4

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

T = TypeVar("T")
_MAX_RETRIES = 3
_RETRY_BASE_DELAY_SEC = 0.5

# Local fallback storage directory (used when MinIO is unavailable)
_LOCAL_STORAGE_ROOT = Path(__file__).resolve().parents[3] / "uploads" / "_local_storage"


class StorageService:
    _use_minio_cached: bool | None = None
    _minio_client = None
    _minio_bucket = None

    def __init__(self) -> None:
        if StorageService._use_minio_cached is None:
            StorageService._use_minio_cached = self._try_init_minio()
        
        self._use_minio = StorageService._use_minio_cached
        if self._use_minio:
            self._minio_client = StorageService._minio_client
            self._minio_bucket = StorageService._minio_bucket
        else:
            logger.warning(
                "MinIO unavailable — using local filesystem fallback at %s",
                _LOCAL_STORAGE_ROOT,
            )
            _LOCAL_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

    def _try_init_minio(self) -> bool:
        try:
            from minio import Minio
            import urllib3

            logger.info("Probing MinIO endpoint at %s...", settings.minio_endpoint)
            # Probe with short timeout to check if MinIO is actually running
            probe_timeout = urllib3.Timeout(connect=1.0, read=2.0)
            probe_client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
                http_client=urllib3.PoolManager(timeout=probe_timeout, retries=False),
            )
            bucket = settings.minio_bucket
            if not probe_client.bucket_exists(bucket):
                probe_client.make_bucket(bucket)

            # Probe succeeded! Now initialize the production client with default/longer timeouts
            StorageService._minio_client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
            StorageService._minio_bucket = bucket
            logger.info("MinIO successfully initialized and using bucket: %s", bucket)
            return True
        except Exception as exc:
            logger.warning(
                "MinIO probing/init failed (will fallback to local filesystem): %s", exc
            )
            return False

    def _retry_s3(self, operation: str, func: Callable[[], T]) -> T:
        last_exc = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                return func()
            except Exception as exc:
                last_exc = exc
                if attempt >= _MAX_RETRIES:
                    break
                delay = _RETRY_BASE_DELAY_SEC * attempt
                logger.warning(
                    "MinIO %s failed (attempt %s/%s), retrying in %.1fs: %s",
                    operation, attempt, _MAX_RETRIES, delay, exc,
                )
                time.sleep(delay)
        logger.error("MinIO %s failed after %s attempts", operation, _MAX_RETRIES)
        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upload_file(self, local_path: Path, prefix: str = "uploads") -> str:
        key = f"{prefix}/{uuid4().hex}/{local_path.name}"
        if self._use_minio:
            def _put() -> None:
                self._minio_client.fput_object(self._minio_bucket, key, str(local_path))
            self._retry_s3("upload_file", _put)
        else:
            dest = _LOCAL_STORAGE_ROOT / key
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local_path, dest)
        return key

    def upload_bytes(self, data: bytes, filename: str, prefix: str = "artifacts") -> str:
        key = f"{prefix}/{uuid4().hex}/{filename}"
        if self._use_minio:
            def _put() -> None:
                self._minio_client.put_object(
                    self._minio_bucket, key, BytesIO(data), length=len(data)
                )
            self._retry_s3("upload_bytes", _put)
        else:
            dest = _LOCAL_STORAGE_ROOT / key
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        return key

    def download_to_path(self, key: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if self._use_minio:
            def _get() -> None:
                self._minio_client.fget_object(self._minio_bucket, key, str(dest))
            self._retry_s3("download_to_path", _get)
        else:
            src = _LOCAL_STORAGE_ROOT / key
            if not src.exists():
                raise FileNotFoundError(f"Local storage key not found: {key}")
            shutil.copy2(src, dest)
        return dest

    def get_presigned_url(self, key: str, expires_hours: int = 1) -> str:
        if self._use_minio:
            from datetime import timedelta
            return self._minio_client.presigned_get_object(
                self._minio_bucket, key, expires=timedelta(hours=expires_hours)
            )
        # Return a local path URL for dev
        local_path = _LOCAL_STORAGE_ROOT / key
        return f"/dev-storage/{key}" if local_path.exists() else ""
