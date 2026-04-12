from typing import Protocol

from app.models.domain import MedicationRecord


class MedicationRepository(Protocol):
    def list_medications(self) -> list[MedicationRecord]:
        """Return medication records used for lookup."""

    def update_audio_reference(self, medication_id: int, s3_key: str, audio_url: str) -> MedicationRecord:
        """Persist reusable medication audio metadata."""
