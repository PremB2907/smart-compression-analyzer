"""S3 storage implementation for Floci / AWS object storage."""

from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from botocore.exceptions import ClientError

from app.config import get_settings
from app.services.cloud.client import get_s3_client

logger = logging.getLogger(__name__)


class S3StorageEngine:
    def __init__(self, bucket: str | None = None) -> None:
        self.settings = get_settings()
        self.bucket = bucket or self.settings.s3_bucket
        self.s3 = get_s3_client()
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self.s3.head_bucket(Bucket=self.bucket)
        except ClientError:
            try:
                if self.settings.aws_region == "us-east-1":
                    self.s3.create_bucket(Bucket=self.bucket)
                else:
                    self.s3.create_bucket(
                        Bucket=self.bucket,
                        CreateBucketConfiguration={"LocationConstraint": self.settings.aws_region},
                    )
                logger.info("Created S3 bucket: %s", self.bucket)
            except Exception as e:
                logger.warning("Could not auto-create S3 bucket %s: %s", self.bucket, e)

    def upload_file(self, local_path: Path, prefix: str = "uploads") -> str:
        key = f"{prefix}/{uuid4().hex}/{local_path.name}"
        try:
            self.s3.upload_file(str(local_path), self.bucket, key)
            return key
        except Exception as exc:
            logger.error("Failed to upload file to S3 s3://%s/%s: %s", self.bucket, key, exc)
            raise

    def upload_bytes(self, data: bytes, filename: str, prefix: str = "artifacts") -> str:
        key = f"{prefix}/{uuid4().hex}/{filename}"
        try:
            self.s3.upload_fileobj(BytesIO(data), self.bucket, key)
            return key
        except Exception as exc:
            logger.error("Failed to upload bytes to S3 s3://%s/%s: %s", self.bucket, key, exc)
            raise

    def download_to_path(self, key: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.s3.download_file(self.bucket, key, str(dest))
            return dest
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in ("404", "NoSuchKey"):
                raise FileNotFoundError(f"S3 object not found: s3://{self.bucket}/{key}") from exc
            raise

    def get_presigned_url(self, key: str, expires_hours: int = 1) -> str:
        try:
            url = self.s3.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_hours * 3600,
            )
            return url
        except Exception as exc:
            logger.warning("Failed to generate presigned URL for key %s: %s", key, exc)
            return ""

    def object_exists(self, key: str) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False
