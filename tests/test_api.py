import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.domain import MedicationExtraction, OCRResult
from app.models.schemas import AnalyzeMedicationResponse, AudioPayload
from app.services.pipeline import MedicationPipelineService


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class DummyOCRProvider:
    def extract_text(self, image_path: str) -> OCRResult:
        return OCRResult(full_text="Tylenol 500 mg tablet", lines=["Tylenol 500 mg tablet"], confidence=0.99)


class DummyExtractionService:
    def extract(self, ocr_text: str) -> MedicationExtraction:
        return MedicationExtraction(drug_name="Tylenol", dose="500 mg", form="tablet", confidence=0.95)


class DummyKBService:
    def lookup(self, extraction: MedicationExtraction):
        from app.models.domain import KBMatchResult, MedicationRecord

        return KBMatchResult(
            matched=True,
            canonical_name="Tylenol",
            match_type="canonical",
            score=1.0,
            record=MedicationRecord(
                canonical_name="Tylenol",
                aliases=["Acetaminophen"],
                strength="500 mg",
                form="tablet",
                purpose="pain relief and fever reduction",
                warnings=["Do not exceed the recommended dose."],
                audio_summary_template="{name}, {dose}. Commonly used for {purpose}. Warning: {warning_short}",
            ),
        )


class DummySummaryService:
    def generate_from_kb(self, match, extraction) -> str:
        return "Tylenol, 500 mg. Commonly used for pain relief and fever reduction."

    def generate_fallback(self) -> str:
        return "fallback"


class DummyMedicationAudioService:
    async def get_audio_for_match(self, match, summary_text: str, request_id: str) -> AudioPayload:
        return AudioPayload(
            content_type="audio/mpeg",
            s3_key="medications/tylenol.mp3",
            url="https://example.com/medications/tylenol.mp3",
            source="medication_audio_cache",
        )

    def fallback_audio(self) -> AudioPayload:
        return AudioPayload(
            content_type="audio/mpeg",
            s3_key="system-audio/fallback-no-match.mp3",
            url="https://example.com/system-audio/fallback-no-match.mp3",
            source="shared_fallback_audio",
        )


@pytest.fixture
def override_pipeline(tmp_path):
    from app.dependencies import get_pipeline_service

    pipeline = MedicationPipelineService(
        ocr_provider=DummyOCRProvider(),
        extraction_service=DummyExtractionService(),
        kb_service=DummyKBService(),
        summary_service=DummySummaryService(),
        medication_audio_service=DummyMedicationAudioService(),
        upload_dir=tmp_path,
    )
    app.dependency_overrides[get_pipeline_service] = lambda: pipeline
    yield
    app.dependency_overrides.clear()


# Branch 11 — invalid file type
def test_invalid_file_type_rejected() -> None:
    response = client.post(
        "/analyze-medication",
        files={"file": ("doc.pdf", b"fake-bytes", "application/pdf")},
    )
    assert response.status_code == 400
    assert "jpg" in response.json()["detail"].lower()


# Branch 12 — AudioUnavailableError returns error audio
class DummyAudioFailPipelineService:
    async def analyze(self, file, request_id):
        from app.core.exceptions import AudioUnavailableError
        raise AudioUnavailableError("TTS crashed")


@pytest.fixture
def override_pipeline_audio_error():
    from app.dependencies import get_pipeline_service
    app.dependency_overrides[get_pipeline_service] = lambda: DummyAudioFailPipelineService()
    yield
    app.dependency_overrides.clear()


def test_audio_unavailable_returns_error_audio(override_pipeline_audio_error) -> None:
    response = client.post(
        "/analyze-medication",
        files={"file": ("label.png", b"fake-image-bytes", "image/png")},
    )
    assert response.status_code == 500
    assert response.json()["audio"]["source"] == "error_audio"


def test_analyze_endpoint_with_mocks(override_pipeline) -> None:
    response = client.post(
        "/analyze-medication",
        files={"file": ("label.png", b"fake-image-bytes", "image/png")},
    )
    assert response.status_code == 200
    payload = AnalyzeMedicationResponse.model_validate(response.json())
    assert payload.summary.source == "structured_kb"
    assert payload.audio.source == "medication_audio_cache"
    assert payload.audio.s3_key == "medications/tylenol.mp3"
