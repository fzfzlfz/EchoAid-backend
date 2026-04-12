from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class MedicationORM(Base):
    __tablename__ = "medications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    aliases: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    dose_forms: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    common_strengths: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    audio_summary_template: Mapped[str] = mapped_column(Text, nullable=False)
    audio_s3_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    audio_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    audio_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
