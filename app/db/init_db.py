import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import BASE_DIR
from app.db.models import Base, MedicationORM
from app.db.session import engine


def create_schema() -> None:
    Base.metadata.create_all(bind=engine)


def migrate_schema() -> None:
    """Apply incremental schema changes to existing databases."""
    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE medications ADD COLUMN IF NOT EXISTS audio_s3_key VARCHAR(500)"
        ))
        conn.commit()


def reset_schema() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def seed_medications_from_json(
    session: Session,
    seed_path: Path = BASE_DIR / "data" / "medications.json",
) -> int:
    with seed_path.open("r", encoding="utf-8") as seed_file:
        records = json.load(seed_file)

    inserted = 0
    for record in records:
        exists = (
            session.query(MedicationORM)
            .filter(
                MedicationORM.canonical_name == record["canonical_name"],
                MedicationORM.strength == record["strength"],
                MedicationORM.form == record["form"],
            )
            .first()
        )
        if exists:
            continue

        session.add(
            MedicationORM(
                canonical_name=record["canonical_name"],
                aliases=record.get("aliases", []),
                strength=record["strength"],
                form=record["form"],
                purpose=record["purpose"],
                warnings=record.get("warnings", []),
                audio_summary_template=record["audio_summary_template"],
            )
        )
        inserted += 1

    session.commit()
    return inserted


def bootstrap_database() -> None:
    create_schema()
    with Session(engine) as session:
        seed_medications_from_json(session)


if __name__ == "__main__":
    bootstrap_database()
