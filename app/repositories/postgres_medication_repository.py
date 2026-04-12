from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from app.db.models import MedicationORM
from app.models.domain import MedicationRecord


class PostgresMedicationRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def list_medications(self) -> list[MedicationRecord]:
        with self.session_factory() as session:
            rows = session.query(MedicationORM).all()
            return [self._to_domain(row) for row in rows]

    def update_audio_reference(self, medication_id: int, s3_key: str, audio_url: str) -> MedicationRecord:
        with self.session_factory() as session:
            row = session.get(MedicationORM, medication_id)
            if row is None:
                raise ValueError(f"Medication not found: {medication_id}")

            row.audio_s3_key = s3_key
            row.audio_url = audio_url
            row.audio_updated_at = datetime.now(UTC)
            session.commit()
            session.refresh(row)
            return self._to_domain(row)

    @staticmethod
    def _to_domain(row: MedicationORM) -> MedicationRecord:
        return MedicationRecord(
            id=row.id,
            canonical_name=row.canonical_name,
            aliases=row.aliases or [],
            dose_forms=row.dose_forms or [],
            common_strengths=row.common_strengths or [],
            purpose=row.purpose,
            warnings=row.warnings or [],
            audio_summary_template=row.audio_summary_template,
            audio_s3_key=row.audio_s3_key,
            audio_url=row.audio_url,
            audio_updated_at=row.audio_updated_at,
        )
