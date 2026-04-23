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

    @staticmethod
    def _to_domain(row: MedicationORM) -> MedicationRecord:
        return MedicationRecord(
            id=row.id,
            canonical_name=row.canonical_name,
            aliases=row.aliases or [],
            strength=row.strength,
            form=row.form,
            purpose=row.purpose,
            warnings=row.warnings or [],
            audio_summary_template=row.audio_summary_template,
        )
