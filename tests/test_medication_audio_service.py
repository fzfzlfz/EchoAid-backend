from pathlib import Path

from app.core.config import Settings
from app.models.domain import KBMatchResult, MedicationRecord
from app.services.medication_audio_service import MedicationAudioService


class SpyTTSService:
    def __init__(self, output_path: Path) -> None:
        self.calls: list[str] = []
        self._output_path = output_path

    def synthesize(self, text: str, request_id: str) -> Path:
        self.calls.append(request_id)
        self._output_path.touch()
        return self._output_path


class SpyCompressionService:
    def __init__(self, output_path: Path) -> None:
        self.calls: list[str] = []
        self._output_path = output_path

    def compress(self, input_path: Path, request_id: str, output_dir: Path) -> Path:
        self.calls.append(request_id)
        self._output_path.touch()
        return self._output_path


class SpyStorageService:
    def __init__(self) -> None:
        self.uploaded: list[str] = []

    def upload_audio(self, file_path: Path, s3_key: str) -> str:
        self.uploaded.append(s3_key)
        return f"https://example.com/{s3_key}"

    def presign_url(self, s3_key: str, expiry: int = 604800) -> str:
        return f"https://example.com/presigned/{s3_key}"


def _settings() -> Settings:
    return Settings(
        FALLBACK_AUDIO_S3_KEY="system-audio/fallback-no-match.mp3",
        FALLBACK_AUDIO_URL="https://example.com/system-audio/fallback-no-match.mp3",
    )


def _record() -> MedicationRecord:
    return MedicationRecord(
        id=1,
        canonical_name="Tylenol",
        aliases=["Acetaminophen"],
        strength="500mg",
        form="tablet",
        purpose="pain relief and fever reduction",
        warnings=["Do not exceed the recommended dose."],
        audio_summary_template="{name}, {strength}, {form}. Commonly used for {purpose}. Warning: {warning_short}",
    )


def test_get_audio_generates_fresh_audio_per_request(tmp_path: Path) -> None:
    wav = tmp_path / "out.wav"
    mp3 = tmp_path / "out.mp3"
    tts = SpyTTSService(wav)
    compression = SpyCompressionService(mp3)
    storage = SpyStorageService()

    service = MedicationAudioService(
        tts_service=tts,
        compression_service=compression,
        storage_service=storage,
        audio_dir=tmp_path,
        settings=_settings(),
    )

    audio = service.get_audio_for_match(
        KBMatchResult(matched=True, canonical_name="Tylenol", record=_record()),
        "Tylenol summary",
        "req-abc",
    )

    assert tts.calls == ["req-abc"]
    assert compression.calls == ["req-abc"]
    assert storage.uploaded == ["medications/req-abc.mp3"]
    assert audio.s3_key == "medications/req-abc.mp3"
    assert audio.source == "generated_medication_audio"


def test_fallback_audio_uses_shared_s3_reference() -> None:
    service = MedicationAudioService(
        tts_service=None,
        compression_service=None,
        storage_service=None,
        audio_dir=Path("storage/audio"),
        settings=_settings(),
    )
    audio = service.fallback_audio()
    assert audio.source == "shared_fallback_audio"
    assert audio.s3_key == "system-audio/fallback-no-match.mp3"
    assert audio.url == "https://example.com/system-audio/fallback-no-match.mp3"
