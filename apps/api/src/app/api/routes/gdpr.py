"""Endpoints RGPD (Phase 5) — réservés aux administrateurs.

- `GET /gdpr/candidates/{id}/export` : export complet des données d'un candidat
  (droit d'accès). Chaque export est tracé dans le journal d'audit.
- `GET /gdpr/retention/preview` : aperçu (dry-run) de la purge par rétention —
  liste ce qui SERAIT supprimé, sans rien supprimer.

⚠️ La purge réelle est IRRÉVERSIBLE : elle n'est PAS exposée en HTTP. Elle
s'exécute via la tâche planifiée Arq (`app.worker`) ou, manuellement, via le
script `app.scripts.purge_candidates` (dry-run par défaut, confirmation
explicite requise pour supprimer).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import SessionDep, require_role
from app.core.config import settings
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.gdpr import CandidateExport, PurgePreview
from app.services import audit, gdpr
from app.services import candidates as candidates_service

router = APIRouter(tags=["gdpr"])

# Toutes les opérations RGPD sont réservées aux administrateurs (RBAC existant).
AdminUser = Annotated[User, Depends(require_role(UserRole.admin))]


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get(
    "/candidates/{candidate_id}/export",
    response_model=CandidateExport,
    summary="Export RGPD complet d'un candidat (admin — droit d'accès)",
)
async def export_candidate(
    request: Request,
    candidate_id: uuid.UUID,
    session: SessionDep,
    admin: AdminUser,
) -> CandidateExport:
    candidate = await candidates_service.get_candidate(session, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidat introuvable.")
    export = await gdpr.build_candidate_export(session, candidate, exported_by=admin.email)
    # Traçabilité RGPD : qui a exporté quoi, quand.
    await audit.record(
        session,
        action="gdpr.export",
        user_id=admin.id,
        entity_type="candidate",
        entity_id=candidate_id,
        ip_address=_client_ip(request),
    )
    await session.commit()
    return export


@router.get(
    "/retention/preview",
    response_model=PurgePreview,
    summary="Aperçu (dry-run) de la purge par rétention (admin)",
    description=(
        "Liste les candidats qui SERAIENT purgés selon la politique de rétention "
        "(RETENTION_DAYS), sans rien supprimer. Les CV migrés du POC sont exclus. "
        "Si RETENTION_DAYS=0, la purge est désactivée (`enabled=false`)."
    ),
)
async def preview_retention_purge(
    request: Request,
    session: SessionDep,
    admin: AdminUser,
) -> PurgePreview:
    preview = await gdpr.preview_purge(
        session,
        retention_days=settings.retention_days,
        batch_limit=settings.retention_purge_batch_limit,
    )
    # Trace la consultation de l'aperçu (lecture seule, aucune suppression).
    await audit.record(
        session,
        action="gdpr.purge.preview",
        user_id=admin.id,
        entity_type="candidate",
        details={"retention_days": preview.retention_days, "total": preview.total},
        ip_address=_client_ip(request),
    )
    await session.commit()
    return preview
