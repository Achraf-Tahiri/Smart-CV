"""Modèles candidat et document (fichier CV)."""

import uuid

from sqlalchemy import BigInteger, Computed, Float, ForeignKey, Index, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey
from app.models.enums import CandidateStatus, Source


class Candidate(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "candidates"
    # Index plein-texte (recherche hybride, Phase 2.4).
    __table_args__ = (
        Index("ix_candidates_search_vector", "search_vector", postgresql_using="gin"),
    )

    prenom: Mapped[str | None] = mapped_column(String(255))
    nom: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    telephone: Mapped[str | None] = mapped_column(String(50))
    ville: Mapped[str | None] = mapped_column(String(255), index=True)
    poste_actuel: Mapped[str | None] = mapped_column(String(255))
    secteur: Mapped[str | None] = mapped_column(String(255), index=True)
    specialite: Mapped[str | None] = mapped_column(String(255))
    annees_experience: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    experience_texte: Mapped[str | None] = mapped_column(String(100))
    seniorite: Mapped[str | None] = mapped_column(String(50), index=True)
    status: Mapped[CandidateStatus] = mapped_column(
        SAEnum(CandidateStatus, native_enum=False, length=20, name="candidate_status"),
        nullable=False,
        default=CandidateStatus.pending,
        index=True,
    )
    source: Mapped[Source] = mapped_column(
        SAEnum(Source, native_enum=False, length=20, name="candidate_source"),
        nullable=False,
    )
    # Sortie brute du LLM, conservée telle quelle (on ne perd rien).
    raw_extraction: Mapped[dict | None] = mapped_column(JSONB)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    # Texte concaténé pour la recherche plein-texte (rempli à l'ingestion) et
    # tsvector généré (indexé, GIN) — recherche hybride Phase 2.4.
    search_text: Mapped[str | None] = mapped_column(Text)
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('french', coalesce(search_text, ''))", persisted=True),
    )


class Document(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "documents"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    # SHA-256 du contenu : déduplication forte (un même fichier importé une seule fois).
    file_hash: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    source: Mapped[Source] = mapped_column(
        SAEnum(Source, native_enum=False, length=20, name="document_source"),
        nullable=False,
    )
    drive_file_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    drive_view_url: Mapped[str | None] = mapped_column(String(1024))
