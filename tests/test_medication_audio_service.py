from pathlib import Path

from app.core.config import Settings
from app.models.domain import KBMatchResult, MedicationRecord
from app.services.medication_audio_service import MedicationAudioService


class DummyRepository:
    def __init__(self) -> None:
        self.updated = False

    def list_medications(self) -> list[MedicationRecord]:
        return []

    def update_audio_reference(self, medication_id: int, s3_key: str, audio_url: str) -> MedicationRecord:
        self.updated = True
        raise AssertionError("Cached audio should not update the DB.")


class FailingTTSService:
    def synthesize(self, text: str, request_id: str) -> Path:
        raise AssertionError("Cached audio should not call TTS.")


class FailingCompressionService:
    def compress(self, input_path: Path, request_id: str, output_dir: Path) -> Path:
        raise AssertionError("Cached audio should not call FFmpeg.")


class FailingStorageService:
    def upload_audio(self, file_path: Path, s3_key: str) -> str:
        raise AssertionError("Cached audio should not upload to S3.")


def _settings() -> Settings:
    return Settings(
        FALLBACK_AUDIO_S3_KEY="system-audio/fallback-no-match.mp3",
        FALLBACK_AUDIO_URL="https://example.com/system-audio/fallback-no-match.mp3",
    )


def _service() -> MedicationAudioService:
    return MedicationAudioService(
        repository=DummyRepository(),
        tts_service=FailingTTSService(),
        compression_service=FailingCompressionService(),
        storage_service=FailingStorageService(),
        audio_dir=Path("storage/audio"),
        settings=_settings(),
    )


def test_cached_medication_audio_skips_generation() -> None:
    record = MedicationRecord(
        id=1,
        canonical_name="Tylenol",
        aliases=["Acetaminophen"],
        dose_forms=["tablet"],
        common_strengths=["500 mg"],
        purpose="pain relief and fever reduction",
        warnings=["Do not exceed the recommended dose."],
        audio_summary_template="{name}, {dose}. Commonly used for {purpose}. Warning: {warning_short}",
        audio_s3_key="medications/tylenol.mp3",
        audio_url="https://example.com/medications/tylenol.mp3",
    )
    audio = _service().get_audio_for_match(
        KBMatchResult(matched=True, canonical_name="Tylenol", record=record),
        "Tylenol summary",
        "request-id",
    )

    assert audio.source == "medication_audio_cache"
    assert audio.s3_key == "medications/tylenol.mp3"


def test_fallback_audio_uses_shared_s3_reference() -> None:
    audio = _service().fallback_audio()
    assert audio.source == "shared_fallback_audio"
    assert audio.s3_key == "system-audio/fallback-no-match.mp3"
    assert audio.url == "https://example.com/system-audio/fallback-no-match.mp3"
