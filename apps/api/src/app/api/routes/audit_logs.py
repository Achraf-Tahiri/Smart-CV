"""Consultation du journal d'audit — réservé aux administrateurs (traçabilité RGPD)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import SessionDep, require_role
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.audit import AuditLogRead
from app.schemas.common import Page
from app.services import audit

router = APIRouter(tags=["audit"])

AdminUser = Annotated[User, Depends(require_role(UserRole.admin))]


@router.get("", response_model=Page[AuditLogRead], summary="Journal d'audit (admin)")
async def list_audit_logs(
    session: SessionDep,
    _admin: AdminUser,
    action: str | None = None,
    user_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[AuditLogRead]:
    total, items = await audit.list_audit_logs(
        session, action=action, user_id=user_id, limit=limit, offset=offset
    )
    return Page(
        total=total,
        items=[AuditLogRead.model_validate(i) for i in items],
        limit=limit,
        offset=offset,
    )
