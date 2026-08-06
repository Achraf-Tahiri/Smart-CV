"""Modèles du parcours : expériences, formations, activités extra."""

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKey


class Experience(UUIDPrimaryKey, Base):
    __tablename__ = "experiences"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    poste: Mapped[str | None] = mapped_column(String(255))
    entreprise: Mapped[str | None] = mapped_column(String(255))
    date_debut: Mapped[date | None] = mapped_column(Date)
    date_fin: Mapped[date | None] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str | None] = mapped_column(Text)


class Education(UUIDPrimaryKey, Base):
    __tablename__ = "educations"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    diplome: Mapped[str | None] = mapped_column(String(255))
    ecole: Mapped[str | None] = mapped_column(String(255))
    annee: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)


class ExtraActivity(UUIDPrimaryKey, Base):
    __tablename__ = "extra_activities"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    titre: Mapped[str | None] = mapped_column(String(255))
    organisation: Mapped[str | None] = mapped_column(String(255))
    date_debut: Mapped[date | None] = mapped_column(Date)
    date_fin: Mapped[date | None] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str | None] = mapped_column(Text)
