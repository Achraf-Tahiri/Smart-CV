"""Suivi des traitements : jobs d'import et état de synchro Drive."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKey
from app.models.enums import ImportJobSource, ImportJobStatus


class ImportJob(UUIDPrimaryKey, Base):
    __tablename__ = "import_jobs"

    source: Mapped[ImportJobSource] = mapped_column(
        SAEnum(ImportJobSource, native_enum=False, length=20, name="import_job_source"),
        nullable=False,
    )
    status: Mapped[ImportJobStatus] = mapped_column(
        SAEnum(ImportJobStatus, native_enum=False, length=20, name="import_job_status"),
        nullable=False,
        default=ImportJobStatus.queued,
        index=True,
    )
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("candidates.id", ondelete="SET NULL")
    )
    error_log: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SyncState(UUIDPrimaryKey, Base):
    """État de synchronisation incrémentale d'un dossier Google Drive (Phase 3)."""

    __tablename__ = "sync_state"

    drive_folder_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cursor: Mapped[str | None] = mapped_column(String(512))
