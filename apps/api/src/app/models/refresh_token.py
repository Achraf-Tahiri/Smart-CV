"""Jetons de rafraîchissement (Phase 5c) : session longue durée, révocable."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKey


class RefreshToken(UUIDPrimaryKey, Base):
    """Un jeton de rafraîchissement, stocké **haché** (jamais en clair).

    Rotation : à chaque usage, le jeton est révoqué et remplacé par un nouveau
    (`replaced_by_id`), ce qui permet de détecter le rejeu d'un jeton déjà utilisé.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
