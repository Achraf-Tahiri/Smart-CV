"""Endpoints admin — synchronisation Google Drive (Phase 3b).

- `POST /api/v1/drive/sync` : met en file une synchro (202 Accepted).
- `GET  /api/v1/drive/sync-state` : lit l'état courant (dernière synchro).

Réservés à l'admin. La synchro elle-même tourne dans le worker Arq (jamais
dans le cycle HTTP) — l'API ne fait qu'enfiler et lire l'état.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import SessionDep, require_role
from app.core.config import settings
from app.core.queue import enqueue_drive_sync
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.drive import DriveSyncAccepted, DriveSyncRequest, DriveSyncStateRead
from app.services import audit
from app.services import drive_sync as drive_sync_service

router = APIRouter(tags=["drive"])

AdminUser = Annotated[User, Depends(require_role(UserRole.admin))]


def _resolve_folder_id(explicit: str | None) -> str:
    folder_id = (explicit or settings.google_drive_folder_id or "").strip()
    if not folder_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=("folder_id requis (dans la requête ou via GOOGLE_DRIVE_FOLDER_ID)."),
        )
    return folder_id


@router.post(
    "/sync",
    response_model=DriveSyncAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Déclencher une synchronisation Drive (admin)",
)
async def trigger_sync(
    request: Request,
    session: SessionDep,
    current_user: AdminUser,
    payload: DriveSyncRequest | None = None,
):
    folder_id = _resolve_folder_id(payload.folder_id if payload else None)
    await enqueue_drive_sync(folder_id)
    await audit.record(
        session,
        action="drive.sync.enqueued",
        user_id=current_user.id,
        entity_type="drive_folder",
        entity_id=None,
        details={"folder_id": folder_id},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    return DriveSyncAccepted(folder_id=folder_id)


@router.get(
    "/sync-state",
    response_model=DriveSyncStateRead,
    summary="Consulter l'état de synchronisation d'un dossier (admin)",
)
async def read_sync_state(
    session: SessionDep,
    _current_user: AdminUser,
    folder_id: str | None = None,
):
    resolved = _resolve_folder_id(folder_id)
    state = await drive_sync_service.get_sync_state(session, resolved)
    return DriveSyncStateRead(
        folder_id=resolved,
        last_sync_at=state.last_sync_at if state else None,
        cursor=state.cursor if state else None,
    )
