"""Service métier : candidats (liste filtrée/paginée, CRUD).

Convention : les fonctions ne committent pas (l'appelant gère la transaction).
"""

import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.enums import CandidateStatus
from app.schemas.candidate import CandidateCreate, CandidateUpdate


async def list_candidates(
    session: AsyncSession,
    *,
    q: str | None = None,
    secteur: str | None = None,
    ville: str | None = None,
    seniorite: str | None = None,
    status: CandidateStatus | None = None,
    min_experience: float | None = None,
    max_experience: float | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[int, list[Candidate]]:
    """Retourne (total, éléments de la page) selon les filtres fournis."""
    conditions = []
    if q:
        pattern = f"%{q}%"
        conditions.append(
            or_(
                Candidate.prenom.ilike(pattern),
                Candidate.nom.ilike(pattern),
                Candidate.poste_actuel.ilike(pattern),
                Candidate.email.ilike(pattern),
            )
        )
    if secteur:
        conditions.append(Candidate.secteur == secteur)
    if ville:
        conditions.append(Candidate.ville.ilike(f"%{ville}%"))
    if seniorite:
        conditions.append(Candidate.seniorite == seniorite)
    if status is not None:
        conditions.append(Candidate.status == status)
    if min_experience is not None:
        conditions.append(Candidate.annees_experience >= min_experience)
    if max_experience is not None:
        conditions.append(Candidate.annees_experience <= max_experience)

    where = and_(*conditions) if conditions else None

    count_stmt = select(func.count()).select_from(Candidate)
    if where is not None:
        count_stmt = count_stmt.where(where)
    total = await session.scalar(count_stmt) or 0

    stmt = select(Candidate)
    if where is not None:
        stmt = stmt.where(where)
    stmt = stmt.order_by(Candidate.created_at.desc()).limit(limit).offset(offset)
    rows = list((await session.execute(stmt)).scalars().all())
    return total, rows


async def get_candidate(session: AsyncSession, candidate_id: uuid.UUID) -> Candidate | None:
    """Retourne un candidat par identifiant, ou None."""
    return await session.get(Candidate, candidate_id)


async def create_candidate(
    session: AsyncSession, data: CandidateCreate, *, created_by_id: uuid.UUID | None
) -> Candidate:
    """Crée un candidat (saisie manuelle)."""
    candidate = Candidate(**data.model_dump(), created_by_id=created_by_id)
    session.add(candidate)
    await session.flush()
    return candidate


async def update_candidate(
    session: AsyncSession, candidate: Candidate, data: CandidateUpdate
) -> dict:
    """Applique une mise à jour partielle. Retourne les champs modifiés (pour l'audit)."""
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(candidate, field, value)
    await session.flush()
    return changes


async def delete_candidate(session: AsyncSession, candidate: Candidate) -> None:
    """Supprime un candidat (les enfants suivent via ON DELETE CASCADE)."""
    await session.delete(candidate)
