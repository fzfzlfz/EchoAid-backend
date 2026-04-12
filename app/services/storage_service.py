from pathlib import Path

import boto3

from app.core.exceptions import StorageUploadError


class S3StorageService:
    def __init__(
        self,
        bucket_name: str | None,
        region: str,
        enable_mock: bool = False,
    ) -> None:
        self.bucket_name = bucket_name
        self.region = region
        self.enable_mock = enable_mock
        self.client = None if enable_mock else boto3.client("s3", region_name=region)

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
