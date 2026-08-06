"""Compétences (référentiel global + liaison N-N) et langues."""

import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKey
from app.models.enums import SkillType


class Skill(UUIDPrimaryKey, Base):
    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("name", "type", name="uq_skill_name_type"),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[SkillType] = mapped_column(
        SAEnum(SkillType, native_enum=False, length=10, name="skill_type"), nullable=False
    )


class CandidateSkill(Base):
    """Table de liaison candidat <-> compétence (N-N)."""

    __tablename__ = "candidate_skills"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )


class CandidateLanguage(UUIDPrimaryKey, Base):
    __tablename__ = "candidate_languages"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    level: Mapped[str | None] = mapped_column(String(50))
