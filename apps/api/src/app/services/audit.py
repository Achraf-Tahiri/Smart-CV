"""Service : journal d'audit (traçabilité RGPD — qui a fait quoi, quand).

Réutilisé à chaque action sensible (login, édition, suppression...).
Ne committe pas : l'appelant valide la transaction.
"""

import uuid
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def record(
    session: AsyncSession,
    *,
    action: str,
    user_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Ajoute une entrée au journal d'audit (sans committer)."""
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=ip_address,
    )
    session.add(entry)
    return entry


async def list_audit_logs(
    session: AsyncSession,
    *,
    action: str | None = None,
    user_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[int, list[AuditLog]]:
    """Retourne (total, entrées) du journal d'audit, les plus récentes d'abord."""
    conditions = []
    if action:
        conditions.append(AuditLog.action == action)
    if user_id is not None:
        conditions.append(AuditLog.user_id == user_id)
    where = and_(*conditions) if conditions else None

    count_stmt = select(func.count()).select_from(AuditLog)
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if where is not None:
        count_stmt = count_stmt.where(where)
        stmt = stmt.where(where)

    total = await session.scalar(count_stmt) or 0
    rows = list((await session.execute(stmt.limit(limit).offset(offset))).scalars().all())
    return total, rows
