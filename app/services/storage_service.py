from pathlib import Path

import boto3
from botocore.config import Config

from app.core.exceptions import StorageUploadError


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

        try:
            self.client.upload_file(
                str(file_path),
                self.bucket_name,
                s3_key,
                ExtraArgs={"ContentType": "audio/mpeg"},
            )
            return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
        except Exception as exc:
            raise StorageUploadError("Failed to upload audio to S3.") from exc

    def audio_key_exists(self, s3_key: str) -> bool:
        if self.enable_mock:
            return False
        if not self.bucket_name:
            return False
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except self.client.exceptions.ClientError:
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
