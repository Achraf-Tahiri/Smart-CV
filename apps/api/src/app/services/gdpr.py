"""Service RGPD (Phase 5) : export par candidat et purge par rétention.

Deux briques « RGPD by design » :

A) EXPORT (droit d'accès) — `build_candidate_export` assemble toutes les
   données personnelles d'un candidat (identité + parcours + compétences +
   langues + documents [métadonnées] + sortie brute d'extraction) en réutilisant
   les schémas de fiche détaillée. L'appelant écrit une entrée d'audit.

B) RÉTENTION / PURGE (droit à l'effacement / minimisation) — suppression EN
   CASCADE des candidats trop anciens (au-delà de `retention_days`).

⚠️ La purge est IRRÉVERSIBLE. Garde-fous (défense en profondeur) :
   1. désactivée par défaut (`retention_days <= 0` => aucune suppression) ;
   2. les CV migrés du POC (marqueur `_poc_id` dans `raw_extraction`) sont
      TOUJOURS exclus, quelle que soit la configuration ;
   3. seuls les candidats STRICTEMENT plus anciens que le seuil sont éligibles ;
   4. chaque exécution est plafonnée (`batch_limit`, borne de sécurité) ;
   5. chaque suppression écrit une entrée d'audit (`candidate.purge`).

Convention : les fonctions ne committent pas (l'appelant gère la transaction).
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.schemas.candidate import CandidateRead
from app.schemas.gdpr import CandidateExport, PurgePreview, PurgePreviewItem
from app.services import audit
from app.services import candidates as candidates_service

# Clé-marqueur posée par `migrate_poc.py` sur les CV importés du POC : ces
# enregistrements sont sanctuarisés (jamais purgés automatiquement).
POC_MARKER = "_poc_id"

PURGE_ACTION = "candidate.purge"


# --------------------------------------------------------------------------- #
# A) Export RGPD (droit d'accès)
# --------------------------------------------------------------------------- #
async def build_candidate_export(
    session: AsyncSession, candidate: Candidate, *, exported_by: str
) -> CandidateExport:
    """Assemble l'export RGPD complet d'un candidat (données + parcours + brut)."""
    children = await candidates_service.get_candidate_children(session, candidate.id)
    base = CandidateRead.model_validate(candidate).model_dump()
    return CandidateExport(
        **base,
        **children,
        raw_extraction=candidate.raw_extraction,
        exported_at=datetime.now(UTC),
        exported_by=exported_by,
    )


# --------------------------------------------------------------------------- #
# B) Rétention / purge (droit à l'effacement)
# --------------------------------------------------------------------------- #
def retention_cutoff(retention_days: int, now: datetime | None = None) -> datetime:
    """Date limite : les candidats créés AVANT cette date sont éligibles."""
    now = now or datetime.now(UTC)
    return now - timedelta(days=retention_days)


def _eligible_stmt(retention_days: int, now: datetime | None = None) -> Select:
    """Sélection des candidats éligibles à la purge.

    Un candidat est éligible s'il est plus ancien que le seuil de rétention ET
    qu'il n'est PAS un CV migré du POC (pas de marqueur `_poc_id`).
    """
    cutoff = retention_cutoff(retention_days, now)
    return (
        select(Candidate)
        .where(Candidate.created_at < cutoff)
        .where(
            or_(
                Candidate.raw_extraction.is_(None),
                # jsonb_exists = forme fonction de l'opérateur `?` (évite toute
                # ambiguïté avec le placeholder de asyncpg).
                ~func.jsonb_exists(Candidate.raw_extraction, POC_MARKER),
            )
        )
        .order_by(Candidate.created_at.asc())
    )


async def count_eligible(
    session: AsyncSession, *, retention_days: int, now: datetime | None = None
) -> int:
    """Nombre total de candidats éligibles à la purge (0 si désactivée)."""
    if retention_days <= 0:
        return 0
    stmt = _eligible_stmt(retention_days, now).with_only_columns(func.count()).order_by(None)
    return await session.scalar(stmt) or 0


async def list_expired_candidates(
    session: AsyncSession,
    *,
    retention_days: int,
    limit: int,
    now: datetime | None = None,
) -> list[Candidate]:
    """Liste (bornée) des candidats éligibles à la purge. Vide si désactivée."""
    if retention_days <= 0:
        return []
    stmt = _eligible_stmt(retention_days, now).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def preview_purge(
    session: AsyncSession,
    *,
    retention_days: int,
    batch_limit: int,
    now: datetime | None = None,
) -> PurgePreview:
    """Aperçu (dry-run) : ce qui SERAIT purgé, sans rien supprimer."""
    now = now or datetime.now(UTC)
    enabled = retention_days > 0
    candidates = await list_expired_candidates(
        session, retention_days=retention_days, limit=batch_limit, now=now
    )
    total = await count_eligible(session, retention_days=retention_days, now=now)
    items = [
        PurgePreviewItem(
            id=c.id,
            nom=c.nom,
            prenom=c.prenom,
            email=c.email,
            created_at=c.created_at,
            age_days=(now - c.created_at).days,
        )
        for c in candidates
    ]
    return PurgePreview(
        enabled=enabled,
        retention_days=retention_days,
        cutoff=retention_cutoff(retention_days, now) if enabled else None,
        batch_limit=batch_limit,
        total=total,
        items=items,
    )


async def purge_expired_candidates(
    session: AsyncSession,
    *,
    retention_days: int,
    batch_limit: int,
    actor_id: uuid.UUID | None = None,
    ip_address: str | None = None,
    now: datetime | None = None,
) -> list[dict]:
    """Purge EN CASCADE les candidats éligibles. Retourne la liste des purgés.

    Ne committe pas : l'appelant valide la transaction (permet un rollback en
    cas d'erreur). Chaque suppression écrit une entrée d'audit `candidate.purge`.
    """
    candidates = await list_expired_candidates(
        session, retention_days=retention_days, limit=batch_limit, now=now
    )
    purged: list[dict] = []
    for candidate in candidates:
        # Snapshot minimal AVANT suppression (l'objet devient inaccessible ensuite).
        snapshot = {
            "nom": candidate.nom,
            "prenom": candidate.prenom,
            "email": candidate.email,
            "created_at": candidate.created_at.isoformat(),
            "retention_days": retention_days,
        }
        candidate_id = candidate.id
        # Suppression : les données liées suivent via ON DELETE CASCADE (cascade RGPD).
        await session.delete(candidate)
        await audit.record(
            session,
            action=PURGE_ACTION,
            user_id=actor_id,
            entity_type="candidate",
            entity_id=candidate_id,
            details=snapshot,
            ip_address=ip_address,
        )
        purged.append({"id": str(candidate_id), **snapshot})
    return purged
