import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import BASE_DIR
from app.db.models import Base, MedicationORM
from app.db.session import engine


def create_schema() -> None:
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
            .filter(MedicationORM.canonical_name == record["canonical_name"])
            .first()
        )
        if exists:
            continue

        session.add(
            MedicationORM(
                canonical_name=record["canonical_name"],
                aliases=record.get("aliases", []),
                dose_forms=record.get("dose_forms", []),
                common_strengths=record.get("common_strengths", []),
                purpose=record["purpose"],
                warnings=record.get("warnings", []),
                audio_summary_template=record["audio_summary_template"],
                audio_s3_key=record.get("audio_s3_key"),
                audio_url=record.get("audio_url"),
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
