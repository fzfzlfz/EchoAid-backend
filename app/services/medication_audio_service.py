from pathlib import Path

from app.core.config import Settings
from app.core.exceptions import AppError, AudioUnavailableError
from app.models.domain import KBMatchResult
from app.models.schemas import AudioPayload
from app.services.audio_compression_service import AudioCompressionService
from app.services.tts_service import TextToSpeechService
from app.services.storage_service import S3StorageService


class MedicationAudioService:
    def __init__(
        self,
        tts_service: TextToSpeechService,
        compression_service: AudioCompressionService,
        storage_service: S3StorageService,
        audio_dir: Path,
        settings: Settings,
    ) -> None:
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

        if not record or record.id is None:
            raise AudioUnavailableError("Matched medication record is missing an ID.")

        try:
            raw_audio_path = self.tts_service.synthesize(summary_text, request_id)
            compressed_path = self.compression_service.compress(raw_audio_path, request_id, self.audio_dir)
            s3_key = f"medications/{request_id}.mp3"
            audio_url = self.storage_service.upload_audio(compressed_path, s3_key)
            audio_url = self.storage_service.presign_url(s3_key)
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
