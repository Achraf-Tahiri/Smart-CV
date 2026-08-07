"""Recherche hybride de candidats : plein-texte (tsvector) + vecteurs (pgvector).

Les deux classements sont fusionnés par **RRF** (Reciprocal Rank Fusion) : robuste,
sans réglage de poids. La partie plein-texte fonctionne toujours ; la partie
vectorielle ajoute du sémantique quand des embeddings existent.

Sans texte de requête (`q` vide), on retombe sur un simple listing filtré (récent).
Convention : lecture seule, ne committe pas.
"""

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.embedding import CandidateEmbedding
from app.models.enums import CandidateStatus
from app.providers.embeddings import EmbeddingProvider

# Constante RRF standard (amortit l'influence des rangs élevés).
_RRF_K = 60


def _build_filters(
    secteur: str | None,
    ville: str | None,
    seniorite: str | None,
    status: CandidateStatus | None,
    min_experience: float | None,
    max_experience: float | None,
) -> list:
    conditions = []
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
    return conditions


async def hybrid_search(
    session: AsyncSession,
    embeddings: EmbeddingProvider,
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
    pool: int = 100,
) -> tuple[int, list[Candidate]]:
    """Retourne (total, candidats de la page), classés par pertinence si `q`."""
    conditions = _build_filters(secteur, ville, seniorite, status, min_experience, max_experience)
    where = and_(*conditions) if conditions else None

    # Pas de texte -> simple listing filtré (les plus récents d'abord).
    if not q or not q.strip():
        return await _filtered_listing(session, where, limit, offset)

    ft_ids = await _fulltext_ids(session, q, where, pool)
    vec_ids = await _vector_ids(session, embeddings, q, where, pool)

    # Fusion RRF des deux classements.
    scores: dict = {}
    for ranking in (ft_ids, vec_ids):
        for rank, cid in enumerate(ranking, start=1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (_RRF_K + rank)

    ranked = sorted(scores, key=lambda cid: scores[cid], reverse=True)
    total = len(ranked)
    page_ids = ranked[offset : offset + limit]
    if not page_ids:
        return total, []

    rows = (
        (await session.execute(select(Candidate).where(Candidate.id.in_(page_ids)))).scalars().all()
    )
    by_id = {c.id: c for c in rows}
    ordered = [by_id[cid] for cid in page_ids if cid in by_id]
    return total, ordered


async def _filtered_listing(session, where, limit, offset) -> tuple[int, list[Candidate]]:
    count_stmt = select(func.count()).select_from(Candidate)
    stmt = select(Candidate)
    if where is not None:
        count_stmt = count_stmt.where(where)
        stmt = stmt.where(where)
    total = await session.scalar(count_stmt) or 0
    stmt = stmt.order_by(Candidate.created_at.desc()).limit(limit).offset(offset)
    rows = list((await session.execute(stmt)).scalars().all())
    return total, rows


async def _fulltext_ids(session, q: str, where, pool: int) -> list:
    tsquery = func.websearch_to_tsquery("french", q)
    stmt = select(Candidate.id).where(Candidate.search_vector.op("@@")(tsquery))
    if where is not None:
        stmt = stmt.where(where)
    stmt = stmt.order_by(func.ts_rank(Candidate.search_vector, tsquery).desc()).limit(pool)
    return list((await session.execute(stmt)).scalars().all())


async def _vector_ids(session, embeddings: EmbeddingProvider, q: str, where, pool: int) -> list:
    query_vector = await embeddings.embed_query(q)
    stmt = select(CandidateEmbedding.candidate_id).join(
        Candidate, Candidate.id == CandidateEmbedding.candidate_id
    )
    if where is not None:
        stmt = stmt.where(where)
    stmt = stmt.order_by(CandidateEmbedding.embedding.cosine_distance(query_vector)).limit(pool)
    return list((await session.execute(stmt)).scalars().all())
