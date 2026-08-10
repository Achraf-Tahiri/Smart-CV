"""CRUD candidats.

Contrôle d'accès :
- lecture (liste, détail) : tout utilisateur authentifié (lecteur, recruteur, admin) ;
- écriture (création, édition, suppression) : recruteur (+ admin, toujours autorisé).
Chaque écriture est tracée dans le journal d'audit.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.deps import CurrentUser, EmbeddingsDep, LLMDep, SessionDep, require_role
from app.models.candidate import Candidate
from app.models.enums import CandidateStatus, UserRole
from app.models.user import User
from app.schemas.candidate import (
    CandidateCreate,
    CandidateDetail,
    CandidateRead,
    CandidateStats,
    CandidateUpdate,
)
from app.schemas.common import Page
from app.services import audit
from app.services import candidates as candidates_service
from app.services import nl_search as nl_search_service
from app.services import search as search_service

router = APIRouter(tags=["candidates"])

# Dépendance d'écriture : exige le rôle recruteur (admin toujours autorisé).
WriterUser = Annotated[User, Depends(require_role(UserRole.recruteur))]


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


async def _get_or_404(session: SessionDep, candidate_id: uuid.UUID) -> Candidate:
    candidate = await candidates_service.get_candidate(session, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidat introuvable.")
    return candidate


@router.get("", response_model=Page[CandidateRead], summary="Liste paginée + filtres")
async def list_candidates(
    session: SessionDep,
    _user: CurrentUser,
    q: Annotated[
        str | None, Query(description="Recherche texte : nom, prénom, poste, email.")
    ] = None,
    secteur: str | None = None,
    ville: str | None = None,
    seniorite: str | None = None,
    status_: Annotated[CandidateStatus | None, Query(alias="status")] = None,
    min_experience: Annotated[float | None, Query(ge=0)] = None,
    max_experience: Annotated[float | None, Query(ge=0)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[CandidateRead]:
    total, items = await candidates_service.list_candidates(
        session,
        q=q,
        secteur=secteur,
        ville=ville,
        seniorite=seniorite,
        status=status_,
        min_experience=min_experience,
        max_experience=max_experience,
        limit=limit,
        offset=offset,
    )
    return Page(
        total=total,
        items=[CandidateRead.model_validate(c) for c in items],
        limit=limit,
        offset=offset,
    )


@router.get(
    "/search",
    response_model=Page[CandidateRead],
    summary="Recherche hybride (plein-texte + sémantique) + filtres",
)
async def search_candidates(
    session: SessionDep,
    embeddings: EmbeddingsDep,
    _user: CurrentUser,
    q: Annotated[
        str | None, Query(description="Requête libre (mots-clés, poste, compétence...).")
    ] = None,
    secteur: str | None = None,
    ville: str | None = None,
    seniorite: str | None = None,
    status_: Annotated[CandidateStatus | None, Query(alias="status")] = None,
    min_experience: Annotated[float | None, Query(ge=0)] = None,
    max_experience: Annotated[float | None, Query(ge=0)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[CandidateRead]:
    total, items = await search_service.hybrid_search(
        session,
        embeddings,
        q=q,
        secteur=secteur,
        ville=ville,
        seniorite=seniorite,
        status=status_,
        min_experience=min_experience,
        max_experience=max_experience,
        limit=limit,
        offset=offset,
    )
    return Page(
        total=total,
        items=[CandidateRead.model_validate(c) for c in items],
        limit=limit,
        offset=offset,
    )


@router.get(
    "/nl-search",
    response_model=Page[CandidateRead],
    summary="Recherche en langage naturel",
    description=(
        "Traduit une requête libre (ex : « développeur senior à Casablanca 5 ans ») "
        "en filtres structurés via le LLM, puis exécute la recherche hybride. "
        "Requiert GROQ_API_KEY (ou GEMINI_API_KEY) en production ; "
        "fonctionne sans clé en test via FakeLLMProvider."
    ),
)
async def nl_search_candidates(
    session: SessionDep,
    embeddings: EmbeddingsDep,
    llm: LLMDep,
    _user: CurrentUser,
    q: Annotated[
        str,
        Query(description="Requête en langage naturel (ex : « développeur senior à Casablanca »)."),
    ],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[CandidateRead]:
    total, items = await nl_search_service.nl_search(
        session,
        embeddings,
        llm,
        query=q,
        limit=limit,
        offset=offset,
    )
    return Page(
        total=total,
        items=[CandidateRead.model_validate(c) for c in items],
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=CandidateStats, summary="Statistiques (tableau de bord)")
async def get_stats(session: SessionDep, _user: CurrentUser) -> CandidateStats:
    return CandidateStats(**await candidates_service.candidate_stats(session))


@router.get(
    "/{candidate_id}", response_model=CandidateDetail, summary="Fiche détaillée d'un candidat"
)
async def get_candidate(session: SessionDep, _user: CurrentUser, candidate_id: uuid.UUID):
    candidate = await _get_or_404(session, candidate_id)
    children = await candidates_service.get_candidate_children(session, candidate_id)
    base = CandidateRead.model_validate(candidate).model_dump()
    return CandidateDetail(**base, **children)


@router.post(
    "",
    response_model=CandidateRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un candidat",
)
async def create_candidate(
    request: Request,
    data: CandidateCreate,
    session: SessionDep,
    current_user: WriterUser,
):
    candidate = await candidates_service.create_candidate(
        session, data, created_by_id=current_user.id
    )
    await audit.record(
        session,
        action="candidate.create",
        user_id=current_user.id,
        entity_type="candidate",
        entity_id=candidate.id,
        ip_address=_client_ip(request),
    )
    await session.commit()
    await session.refresh(candidate)
    return candidate


@router.patch("/{candidate_id}", response_model=CandidateRead, summary="Modifier un candidat")
async def update_candidate(
    request: Request,
    candidate_id: uuid.UUID,
    data: CandidateUpdate,
    session: SessionDep,
    current_user: WriterUser,
):
    candidate = await _get_or_404(session, candidate_id)
    changes = await candidates_service.update_candidate(session, candidate, data)
    await audit.record(
        session,
        action="candidate.update",
        user_id=current_user.id,
        entity_type="candidate",
        entity_id=candidate.id,
        details={"changes": changes},
        ip_address=_client_ip(request),
    )
    await session.commit()
    await session.refresh(candidate)
    return candidate


@router.delete(
    "/{candidate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un candidat (RGPD : cascade sur ses données)",
)
async def delete_candidate(
    request: Request,
    candidate_id: uuid.UUID,
    session: SessionDep,
    current_user: WriterUser,
) -> None:
    candidate = await _get_or_404(session, candidate_id)
    # Snapshot pour l'audit avant suppression (l'objet devient inaccessible ensuite).
    snapshot = {"nom": candidate.nom, "prenom": candidate.prenom, "email": candidate.email}
    await candidates_service.delete_candidate(session, candidate)
    await audit.record(
        session,
        action="candidate.delete",
        user_id=current_user.id,
        entity_type="candidate",
        entity_id=candidate_id,
        details=snapshot,
        ip_address=_client_ip(request),
    )
    await session.commit()
