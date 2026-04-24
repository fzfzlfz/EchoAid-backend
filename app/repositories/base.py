from typing import Protocol

from app.models.domain import MedicationRecord


class MedicationRepository(Protocol):
    def list_medications(self) -> list[MedicationRecord]:
        """Return medication records used for lookup."""

