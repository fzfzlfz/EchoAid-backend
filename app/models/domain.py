from datetime import datetime

from pydantic import BaseModel, Field


class OCRResult(BaseModel):
    full_text: str
    lines: list[str] = Field(default_factory=list)
    confidence: float | None = None


class MedicationExtraction(BaseModel):
    drug_name: str | None = None
    dose: str | None = None
    form: str | None = None
    confidence: float = 0.0
    notes: str | None = None


class MedicationRecord(BaseModel):
    id: int | None = None
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    dose_forms: list[str] = Field(default_factory=list)
    common_strengths: list[str] = Field(default_factory=list)
    purpose: str
    warnings: list[str] = Field(default_factory=list)
    audio_summary_template: str
    audio_s3_key: str | None = None
    audio_url: str | None = None
    audio_updated_at: datetime | None = None


class KBMatchResult(BaseModel):
    matched: bool
    canonical_name: str | None = None
    match_type: str | None = None
    score: float | None = None
    record: MedicationRecord | None = None
