from functools import lru_cache
from pathlib import Path

from app.core.config import BASE_DIR, get_settings
from app.db.session import SessionLocal
from app.ocr.google_vision import GoogleVisionOCREngine
from app.ocr.paddle_ocr import PaddleOCREngine
from app.repositories.postgres_medication_repository import PostgresMedicationRepository
from app.services.audio_compression_service import AudioCompressionService
from app.services.extraction_service import ExtractionService
from app.services.kb_service import MedicationKBService
from app.services.medication_audio_service import MedicationAudioService
from app.services.pipeline import MedicationPipelineService
from app.services.summary_service import SummaryService
from app.services.storage_service import S3StorageService
from app.services.tts_service import TextToSpeechService
from app.utils.file_utils import ensure_directory


def _prompt_path() -> Path:
    return BASE_DIR / "app" / "prompts" / "extract_medication.txt"


@lru_cache
def get_medication_repository() -> PostgresMedicationRepository:
    return PostgresMedicationRepository(SessionLocal)


@lru_cache
def get_kb_service() -> MedicationKBService:
    settings = get_settings()
    return MedicationKBService(
        repository=get_medication_repository(),
        match_threshold=settings.kb_match_confidence_threshold,
    )


@lru_cache
def get_summary_service() -> SummaryService:
    return SummaryService()


@lru_cache
def get_extraction_service() -> ExtractionService:
    settings = get_settings()
    return ExtractionService(
        prompt_path=_prompt_path(),
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        enable_mock=settings.enable_mock_services,
    )


@lru_cache
def get_tts_service() -> TextToSpeechService:
    settings = get_settings()
    ensure_directory(settings.audio_dir)
    return TextToSpeechService(
        audio_dir=settings.audio_dir,
        model=settings.openai_tts_model,
        api_key=settings.openai_api_key,
        enable_mock=settings.enable_mock_services,
    )


@lru_cache
def get_audio_compression_service() -> AudioCompressionService:
    settings = get_settings()
    return AudioCompressionService(
        ffmpeg_binary=settings.ffmpeg_binary,
        sample_rate=settings.audio_sample_rate,
        channels=settings.audio_channels,
        bitrate=settings.audio_bitrate,
        output_format=settings.audio_output_format,
        enable_mock=settings.enable_mock_services,
    )


@lru_cache
def get_storage_service() -> S3StorageService:
    settings = get_settings()
    return S3StorageService(
        bucket_name=settings.s3_bucket_name,
        region=settings.aws_region,
        enable_mock=settings.enable_mock_services,
    )


@lru_cache
def get_medication_audio_service() -> MedicationAudioService:
    settings = get_settings()
    ensure_directory(settings.audio_dir)
    return MedicationAudioService(
        repository=get_medication_repository(),
        tts_service=get_tts_service(),
        compression_service=get_audio_compression_service(),
        storage_service=get_storage_service(),
        audio_dir=settings.audio_dir,
        settings=settings,
    )


@lru_cache
def get_ocr_provider():
    settings = get_settings()
    if settings.ocr_provider == "google_vision":
        return GoogleVisionOCREngine()
    return PaddleOCREngine(enable_mock=settings.enable_mock_services)


@lru_cache
def get_pipeline_service() -> MedicationPipelineService:
    settings = get_settings()
    ensure_directory(settings.upload_dir)
    ensure_directory(settings.audio_dir)
    return MedicationPipelineService(
        ocr_provider=get_ocr_provider(),
        extraction_service=get_extraction_service(),
        kb_service=get_kb_service(),
        summary_service=get_summary_service(),
        medication_audio_service=get_medication_audio_service(),
        upload_dir=settings.upload_dir,
    )
