from pydantic import BaseModel, Field


class OCRResult(BaseModel):
    full_text: str
    lines: list[str] = Field(default_factory=list)
    confidence: float | None = None


class MedicationExtraction(BaseModel):
    drug_name: str | None = None
    strength: str | None = None   # e.g. "500mg", "160mg/5mL"
    dose: str | None = None       # dosing instructions e.g. "2 caplets every 6 hours"
    form: str | None = None       # e.g. "tablet", "liquid", "capsule"
    confidence: float = 0.0
    notes: str | None = None


class MedicationRecord(BaseModel):
    id: int | None = None
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    strength: str                  # e.g. "500mg", "160mg/5mL"
    form: str                      # e.g. "caplet", "liquid"
    purpose: str
    warnings: list[str] = Field(default_factory=list)
    audio_summary_template: str
    audio_s3_key: str | None = None


class KBMatchResult(BaseModel):
    matched: bool
    canonical_name: str | None = None
    match_type: str | None = None
    score: float | None = None
    record: MedicationRecord | None = None
