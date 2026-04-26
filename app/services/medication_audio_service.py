import asyncio
from pathlib import Path

from app.core.config import Settings
from app.core.exceptions import AppError, AudioUnavailableError, StorageUploadError
from app.core.logging import get_logger
from app.models.domain import KBMatchResult, MedicationRecord
from app.models.schemas import AudioPayload
from app.services.audio_compression_service import AudioCompressionService
from app.services.tts_service import TextToSpeechService
from app.services.storage_service import S3StorageService

logger = get_logger(__name__)


class MedicationAudioService:
    def __init__(
        self,
        tts_service: TextToSpeechService,
        compression_service: AudioCompressionService,
        storage_service: S3StorageService,
        audio_dir: Path,
        settings: Settings,
        repository=None,
    ) -> None:
        self.tts_service = tts_service
        self.compression_service = compression_service
        self.storage_service = storage_service
        self.audio_dir = audio_dir
        self.settings = settings
        self.repository = repository

    async def get_audio_for_match(
        self,
        match: KBMatchResult,
        summary_text: str,
        request_id: str,
    ) -> AudioPayload:
        record = match.record

        if not record or record.id is None:
            raise AudioUnavailableError("Matched medication record is missing an ID.")

        s3_key = self._build_s3_key(record.canonical_name, record.strength, record.form)

        # Fast path: DB already has a confirmed s3_key — skip S3 HEAD entirely
        if record.audio_s3_key == s3_key:
            logger.info("audio_db_cache_hit key=%s", s3_key)
            try:
                url = self.storage_service.presign_url(s3_key)
                # Fire background verification — doesn't block this request
                asyncio.create_task(self._verify_s3_key_background(record, s3_key))
                return AudioPayload(
                    content_type="audio/mpeg",
                    s3_key=s3_key,
                    url=url,
                    source="cached_medication_audio",
                )
            except StorageUploadError:
                logger.warning("audio_db_cache_stale key=%s clearing_db_entry", s3_key)
                if self.repository:
                    self.repository.clear_audio_s3_key(record.id)

        # Slow path: check S3 HEAD
        loop = asyncio.get_running_loop()
        exists = await loop.run_in_executor(None, self.storage_service.audio_key_exists, s3_key)
        if exists:
            logger.info("audio_cache_hit key=%s", s3_key)
            url = self.storage_service.presign_url(s3_key)
            if self.repository and record.id:
                self.repository.update_audio_s3_key(record.id, s3_key)
            return AudioPayload(
                content_type="audio/mpeg",
                s3_key=s3_key,
                url=url,
                source="cached_medication_audio",
            )

        # Generate, compress, upload
        try:
            raw_audio_path = self.tts_service.synthesize(summary_text, request_id)
            compressed_path = self.compression_service.compress(raw_audio_path, request_id, self.audio_dir)
            self.storage_service.upload_audio(compressed_path, s3_key)
            audio_url = self.storage_service.presign_url(s3_key)
        except AppError as exc:
            raise AudioUnavailableError(
                f"Audio generation failed for '{record.canonical_name}': {exc}"
            ) from exc

        if self.repository and record.id:
            self.repository.update_audio_s3_key(record.id, s3_key)

        return AudioPayload(
            file_path=str(compressed_path),
            content_type="audio/mpeg",
            s3_key=s3_key,
            url=audio_url,
            source="generated_medication_audio",
        )

    async def _verify_s3_key_background(self, record: MedicationRecord, s3_key: str) -> None:
        loop = asyncio.get_running_loop()
        exists = await loop.run_in_executor(None, self.storage_service.audio_key_exists, s3_key)
        if not exists:
            logger.warning("audio_s3_stale_detected key=%s clearing_db_entry", s3_key)
            if self.repository and record.id:
                self.repository.clear_audio_s3_key(record.id)

    @staticmethod
    def _build_s3_key(canonical_name: str, strength: str, form: str) -> str:
        def sanitize(s: str) -> str:
            return s.lower().replace(" ", "_").replace("/", "-")

        return f"medications/{sanitize(canonical_name)}_{sanitize(strength)}_{sanitize(form)}.mp3"

    def fallback_audio(self) -> AudioPayload:
        logger.info("audio_fallback key=%s", self.settings.fallback_audio_s3_key)
        return AudioPayload(
            content_type="audio/mpeg",
            s3_key=self.settings.fallback_audio_s3_key,
            url=self.settings.fallback_audio_url,
            source="shared_fallback_audio",
        )

    def error_audio(self) -> AudioPayload:
        return AudioPayload(
            content_type="audio/mpeg",
            s3_key=self.settings.error_audio_s3_key,
            url=self.settings.error_audio_url,
            source="error_audio",
        )
