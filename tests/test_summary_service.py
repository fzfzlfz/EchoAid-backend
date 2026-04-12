from app.models.domain import KBMatchResult, MedicationExtraction, MedicationRecord
from app.services.summary_service import SummaryService


def _record() -> MedicationRecord:
    return MedicationRecord(
        canonical_name="Tylenol",
        aliases=["Acetaminophen"],
        dose_forms=["tablet"],
        common_strengths=["500 mg"],
        purpose="pain relief and fever reduction",
        warnings=["Do not exceed the recommended dose."],
        audio_summary_template="{name}, {dose}. Commonly used for {purpose}. Warning: {warning_short}",
    )


def test_summary_generation_from_kb() -> None:
    service = SummaryService()
    summary = service.generate_from_kb(
        KBMatchResult(
            matched=True,
            canonical_name="Tylenol",
            match_type="canonical",
            score=1.0,
            record=_record(),
        ),
        MedicationExtraction(drug_name="Tylenol", dose="500 mg"),
    )
    assert "Tylenol, 500 mg." in summary


def test_fallback_summary_generation() -> None:
    service = SummaryService()
    summary = service.generate_fallback()
    assert "I could not confidently identify this medication." in summary
    assert "Please verify with a doctor, pharmacist, or caregiver before taking it." in summary
