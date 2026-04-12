from app.models.domain import MedicationExtraction, MedicationRecord
from app.services.kb_service import MedicationKBService


class InMemoryMedicationRepository:
    def __init__(self) -> None:
        self.records = [
            MedicationRecord(
                id=1,
                canonical_name="Tylenol",
                aliases=["Acetaminophen", "Tylenol Extra Strength"],
                dose_forms=["tablet"],
                common_strengths=["500 mg"],
                purpose="pain relief and fever reduction",
                warnings=["Do not exceed the recommended dose."],
                audio_summary_template="{name}, {dose}. Commonly used for {purpose}. Warning: {warning_short}",
                audio_s3_key="medications/tylenol.mp3",
                audio_url="https://example.com/tylenol.mp3",
            )
        ]

    def list_medications(self) -> list[MedicationRecord]:
        return self.records

    def update_audio_reference(self, medication_id: int, s3_key: str, audio_url: str) -> MedicationRecord:
        raise AssertionError("Not used by these tests.")


def test_kb_exact_alias_match() -> None:
    service = MedicationKBService(InMemoryMedicationRepository())
    result = service.lookup(MedicationExtraction(drug_name="Acetaminophen"))
    assert result.matched is True
    assert result.canonical_name == "Tylenol"
    assert result.match_type == "alias"


def test_kb_no_match() -> None:
    service = MedicationKBService(InMemoryMedicationRepository())
    result = service.lookup(MedicationExtraction(drug_name="Mystery Drug"))
    assert result.matched is False
