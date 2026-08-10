"""Service : jetons de rafraîchissement (Phase 5c).

Stockage **haché** en base (table `refresh_tokens`), avec rotation à l'usage
(un jeton utilisé est révoqué et remplacé) et révocation explicite (logout).
Convention : les fonctions ne committent pas, l'appelant décide.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import generate_refresh_token, hash_refresh_token
from app.models.refresh_token import RefreshToken


async def issue(session: AsyncSession, user_id: uuid.UUID) -> tuple[str, RefreshToken]:
    """Émet un nouveau refresh token pour un utilisateur et le persiste (haché)."""
    raw = generate_refresh_token()
    row = RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(raw),
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
    )
    session.add(row)
    await session.flush()
    return raw, row


async def get_valid(session: AsyncSession, raw_token: str) -> RefreshToken | None:
    """Retourne le jeton s'il existe, n'est ni révoqué ni expiré ; sinon None."""
    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token))
    )
    row = result.scalar_one_or_none()
    if row is None or row.revoked_at is not None:
        return None
    if row.expires_at < datetime.now(UTC):
        return None
    return row


async def rotate(session: AsyncSession, current: RefreshToken) -> tuple[str, RefreshToken]:
    """Révoque `current` et émet son remplaçant (rotation à l'usage)."""
    raw, new_row = await issue(session, current.user_id)
    current.revoked_at = datetime.now(UTC)
    current.replaced_by_id = new_row.id
    session.add(current)
    return raw, new_row


async def revoke(session: AsyncSession, row: RefreshToken) -> None:
    """Révoque un jeton (logout) — idempotent."""
    if row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)
        session.add(row)
