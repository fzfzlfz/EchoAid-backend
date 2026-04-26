import time
from pathlib import Path

import boto3
from botocore.config import Config

from app.core.exceptions import StorageUploadError
from app.core.logging import get_logger

logger = get_logger(__name__)


class S3StorageService:
    def __init__(
        self,
        bucket_name: str | None,
        region: str,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        enable_mock: bool = False,
    ) -> None:
        self.bucket_name = bucket_name
        self.region = region
        self.enable_mock = enable_mock
        self.client = None if enable_mock else boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            endpoint_url=f"https://s3.{region}.amazonaws.com",
            config=Config(signature_version="s3v4"),
        )

    def upload_audio(self, file_path: Path, s3_key: str) -> str:
        if self.enable_mock:
            bucket = self.bucket_name or "mock-bucket"
            return f"https://{bucket}.s3.{self.region}.amazonaws.com/{s3_key}"

        if not self.bucket_name:
            raise StorageUploadError("S3_BUCKET_NAME is missing.")

        t0 = time.perf_counter()
        try:
            self.client.upload_file(
                str(file_path),
                self.bucket_name,
                s3_key,
                ExtraArgs={"ContentType": "audio/mpeg"},
            )
            logger.info("s3_upload_success key=%s s3_upload_ms=%.0f", s3_key, (time.perf_counter() - t0) * 1000)
            return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
        except Exception as exc:
            logger.error("s3_upload_failed key=%s error=%s", s3_key, exc)
            raise StorageUploadError("Failed to upload audio to S3.") from exc

    def audio_key_exists(self, s3_key: str) -> bool:
        if self.enable_mock:
            return False
        if not self.bucket_name:
            return False
        t0 = time.perf_counter()
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info("s3_cache_hit key=%s s3_head_ms=%.0f", s3_key, (time.perf_counter() - t0) * 1000)
            return True
        except self.client.exceptions.ClientError:
            logger.info("s3_cache_miss key=%s s3_head_ms=%.0f", s3_key, (time.perf_counter() - t0) * 1000)
            return False

    def presign_url(self, s3_key: str, expiry: int = 604800) -> str:
        """Return a pre-signed URL (default 7-day expiry)."""
        if self.enable_mock:
            return f"https://{self.bucket_name or 'mock-bucket'}.s3.{self.region}.amazonaws.com/{s3_key}"
        if not self.bucket_name:
            raise StorageUploadError("S3_BUCKET_NAME is missing.")
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": s3_key},
            ExpiresIn=expiry,
        )
