from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    ocr_provider: str = Field(default="paddle", alias="OCR_PROVIDER")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")
    openai_tts_model: str = Field(default="gpt-4o-mini-tts", alias="OPENAI_TTS_MODEL")
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/med_label_reader",
        alias="DATABASE_URL",
    )
    upload_dir: Path = Field(default=BASE_DIR / "storage" / "uploads", alias="UPLOAD_DIR")
    audio_dir: Path = Field(default=BASE_DIR / "storage" / "audio", alias="AUDIO_DIR")
    ffmpeg_binary: str = Field(default="ffmpeg", alias="FFMPEG_BINARY")
    audio_output_format: str = Field(default="mp3", alias="AUDIO_OUTPUT_FORMAT")
    audio_sample_rate: int = Field(default=32000, alias="AUDIO_SAMPLE_RATE")
    audio_channels: int = Field(default=1, alias="AUDIO_CHANNELS")
    audio_bitrate: str = Field(default="64k", alias="AUDIO_BITRATE")
    aws_region: str = Field(default="us-west-2", alias="AWS_REGION")
    s3_bucket_name: str | None = Field(default=None, alias="S3_BUCKET_NAME")
    fallback_audio_s3_key: str = Field(
        default="system-audio/fallback-no-match.mp3",
        alias="FALLBACK_AUDIO_S3_KEY",
    )
    fallback_audio_url: str | None = Field(default=None, alias="FALLBACK_AUDIO_URL")
    error_audio_s3_key: str = Field(
        default="system-audio/error-audio-unavailable.mp3",
        alias="ERROR_AUDIO_S3_KEY",
    )
    error_audio_url: str | None = Field(default=None, alias="ERROR_AUDIO_URL")
    extraction_confidence_threshold: float = Field(
        default=0.65,
        alias="EXTRACTION_CONFIDENCE_THRESHOLD",
    )
    kb_match_confidence_threshold: float = Field(
        default=0.8,
        alias="KB_MATCH_CONFIDENCE_THRESHOLD",
    )
    enable_mock_services: bool = Field(default=False, alias="ENABLE_MOCK_SERVICES")


@lru_cache
def get_settings() -> Settings:
    return Settings()
