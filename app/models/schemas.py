from pydantic import BaseModel, Field

from app.models.domain import KBMatchResult, MedicationExtraction, OCRResult


class SummaryPayload(BaseModel):
    text: str
    source: str


class AudioPayload(BaseModel):
    file_path: str | None = None
    content_type: str | None = None
    s3_key: str | None = None
    url: str | None = None
    source: str | None = None


class AnalyzeMedicationResponse(BaseModel):
    request_id: str
    ocr_text: str
    extraction: MedicationExtraction
    kb_match: KBMatchResult
    summary: SummaryPayload
    audio: AudioPayload
    status: str


class ExtractOnlyRequest(BaseModel):
    ocr_text: str = Field(min_length=1)


class OCRDebugResponse(BaseModel):
    request_id: str
    ocr: OCRResult
