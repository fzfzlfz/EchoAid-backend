from pathlib import Path

from app.core.config import Settings
from app.core.exceptions import AppError, AudioUnavailableError
from app.models.domain import KBMatchResult
from app.models.schemas import AudioPayload
from app.repositories.base import MedicationRepository
from app.services.audio_compression_service import AudioCompressionService
from app.services.tts_service import TextToSpeechService
from app.services.storage_service import S3StorageService
from app.utils.text_normalization import normalize_text


class MedicationAudioService:
    def __init__(
        self,
        repository: MedicationRepository,
        tts_service: TextToSpeechService,
        compression_service: AudioCompressionService,
        storage_service: S3StorageService,
        audio_dir: Path,
        settings: Settings,
    ) -> None:
        self.repository = repository
        self.tts_service = tts_service
        self.compression_service = compression_service
        self.storage_service = storage_service
        self.audio_dir = audio_dir
        self.settings = settings

    def get_audio_for_match(
        self,
        match: KBMatchResult,
        summary_text: str,
        request_id: str,
    ) -> AudioPayload:
        record = match.record
        if record and record.audio_s3_key and record.audio_url:
            return AudioPayload(
                content_type="audio/mpeg",
                s3_key=record.audio_s3_key,
                url=record.audio_url,
                source="medication_audio_cache",
            )

        if not record or record.id is None:
            raise AudioUnavailableError("Matched medication record is missing an ID.")

        try:
            raw_audio_path = self.tts_service.synthesize(summary_text, request_id)
            compressed_path = self.compression_service.compress(raw_audio_path, request_id, self.audio_dir)
            s3_key = f"medications/{record.id}-{normalize_text(record.canonical_name).replace(' ', '-')}.mp3"
            audio_url = self.storage_service.upload_audio(compressed_path, s3_key)
            self.repository.update_audio_reference(record.id, s3_key, audio_url)
        except AppError as exc:
            raise AudioUnavailableError(
                f"Audio generation failed for '{record.canonical_name}': {exc}"
            ) from exc

        return AudioPayload(
            file_path=str(compressed_path),
            content_type="audio/mpeg",
            s3_key=s3_key,
            url=audio_url,
            source="generated_medication_audio",
        )

    def fallback_audio(self) -> AudioPayload:
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
