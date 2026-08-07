"""Pipeline d'ingestion d'un CV (cœur du système).

document stocké -> extraction texte (pdf/docx/ocr) -> extraction LLM structurée
-> normalisation (logique métier pure) -> persistance normalisée (candidat +
expériences/formations/activités/compétences/langues) -> embedding -> statut.

Idempotent : re-traiter un document remet à zéro les données dérivées du candidat.
Convention : ne committe pas (l'appelant gère la transaction). Les erreurs de
traitement ne sont PAS levées : le candidat passe en `manual_review` et un
`ImportJob` en `failed` est enregistré (traçabilité).
"""

import re
import uuid
from datetime import UTC, datetime

from anyio import to_thread
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.cleaning import format_title, normalize_city, normalize_skills
from app.domain.experience import RawPeriod, compute_experience, normalize_period
from app.models.candidate import Candidate, Document
from app.models.embedding import CandidateEmbedding
from app.models.enums import (
    CandidateStatus,
    ImportJobSource,
    ImportJobStatus,
    SkillType,
)
from app.models.experience import Education, Experience, ExtraActivity
from app.models.job import ImportJob
from app.models.skill import CandidateLanguage, CandidateSkill, Skill
from app.providers.embeddings import EmbeddingProvider
from app.providers.llm import LLMError, LLMProvider
from app.schemas.extraction import CVExtraction
from app.services.extraction import extract_cv
from app.services.text_extraction import TextExtractionError, extract_text


async def process_document(
    session: AsyncSession,
    *,
    document: Document,
    llm: LLMProvider,
    embeddings: EmbeddingProvider,
    storage,
) -> Candidate:
    """Traite un document et met à jour le candidat associé. Ne lève pas."""
    candidate = await session.get(Candidate, document.candidate_id)
    if candidate is None:
        raise ValueError("Candidat introuvable pour ce document.")

    job = ImportJob(
        source=ImportJobSource.local_upload,
        status=ImportJobStatus.running,
        candidate_id=candidate.id,
        started_at=datetime.now(UTC),
    )
    session.add(job)
    candidate.status = CandidateStatus.processing
    await session.flush()

    try:
        data = await storage.get(document.storage_key)
        text = await to_thread.run_sync(_extract_text, data, document.filename)
        extraction = await extract_cv(llm, text)

        await apply_extraction(session, candidate, extraction, embeddings)
        candidate.status = CandidateStatus.success
        job.status = ImportJobStatus.success
    except (TextExtractionError, LLMError, ValueError) as exc:
        candidate.status = CandidateStatus.manual_review
        job.status = ImportJobStatus.failed
        job.error_log = str(exc)
    finally:
        job.finished_at = datetime.now(UTC)
        await session.flush()

    return candidate


async def apply_extraction(
    session: AsyncSession,
    candidate: Candidate,
    extraction: CVExtraction,
    embeddings: EmbeddingProvider,
) -> None:
    """Applique une extraction structurée à un candidat : champs + parcours +
    compétences + langues + embedding (réinitialise d'abord les données dérivées).

    Cœur réutilisable : appelé par le worker (après extraction LLM) ET par la
    migration des données du POC (extraction déjà connue).
    """
    await _reset_candidate_children(session, candidate.id)
    _apply_scalar_fields(candidate, extraction)
    _apply_experience(candidate, extraction)
    _persist_children(session, candidate.id, extraction)
    await _persist_children_skills(session, candidate.id, extraction)
    candidate.search_text = _searchable_text(candidate, extraction)
    await _persist_embedding(session, candidate, embeddings)
    candidate.raw_extraction = extraction.model_dump()


def _extract_text(data: bytes, filename: str) -> str:
    text = extract_text(data, filename=filename)
    if not text.strip():
        raise TextExtractionError("Aucun texte exploitable extrait du document.")
    return text


async def _reset_candidate_children(session: AsyncSession, candidate_id: uuid.UUID) -> None:
    """Supprime les données dérivées (ré-ingestion idempotente)."""
    for model in (Experience, Education, ExtraActivity, CandidateLanguage, CandidateSkill):
        await session.execute(delete(model).where(model.candidate_id == candidate_id))
    await session.execute(
        delete(CandidateEmbedding).where(CandidateEmbedding.candidate_id == candidate_id)
    )


def _clip(value: str | None, length: int) -> str | None:
    """Borne une chaîne à la taille de la colonne (robustesse : le LLM ou le POC
    peuvent renvoyer des valeurs anormalement longues). Vide -> None."""
    if value is None:
        return None
    value = value.strip()
    return value[:length] if value else None


def _apply_scalar_fields(candidate: Candidate, ex: CVExtraction) -> None:
    candidate.prenom = _clip(format_title(ex.prenom), 255)
    candidate.nom = _clip(format_title(ex.nom), 255)
    candidate.email = _clip(ex.email, 255)
    candidate.telephone = _clip(ex.telephone, 50)
    candidate.ville = _clip(normalize_city(ex.ville), 255)
    candidate.poste_actuel = _clip(format_title(ex.poste_actuel), 255)
    candidate.secteur = ex.secteur  # issu de la taxonomie, taille sûre
    candidate.specialite = _clip(ex.specialite, 255)


def _apply_experience(candidate: Candidate, ex: CVExtraction) -> None:
    raw_periods = [RawPeriod(e.date_debut, e.date_fin) for e in ex.experiences]
    result = compute_experience(raw_periods)
    candidate.annees_experience = result.years
    candidate.experience_texte = result.label
    candidate.seniorite = result.seniority


def _persist_children(session: AsyncSession, candidate_id: uuid.UUID, ex: CVExtraction) -> None:
    for e in ex.experiences:
        period = normalize_period(
            RawPeriod(e.date_debut, e.date_fin), today=datetime.now(UTC).date()
        )
        session.add(
            Experience(
                candidate_id=candidate_id,
                poste=_clip(e.poste, 255),
                entreprise=_clip(e.entreprise, 255),
                date_debut=period.start if period else None,
                date_fin=(
                    None if (period and period.is_present) else (period.end if period else None)
                ),
                is_current=bool(period and period.is_present),
                description=e.description,
            )
        )
    for f in ex.formations:
        session.add(
            Education(
                candidate_id=candidate_id,
                diplome=_clip(f.diplome, 255),
                ecole=_clip(f.ecole, 255),
                annee=_parse_year(f.annee),
            )
        )
    for a in ex.activites_extra:
        period = normalize_period(
            RawPeriod(a.date_debut, a.date_fin), today=datetime.now(UTC).date()
        )
        session.add(
            ExtraActivity(
                candidate_id=candidate_id,
                titre=_clip(a.titre, 255),
                organisation=_clip(a.organisation, 255),
                date_debut=period.start if period else None,
                date_fin=(
                    None if (period and period.is_present) else (period.end if period else None)
                ),
                is_current=bool(period and period.is_present),
                description=a.description,
            )
        )
    for raw_name, raw_level in (_parse_language(s) for s in ex.langues):
        name = _clip(raw_name, 100)
        if name:
            session.add(
                CandidateLanguage(candidate_id=candidate_id, name=name, level=_clip(raw_level, 50))
            )


async def _persist_children_skills(
    session: AsyncSession, candidate_id: uuid.UUID, ex: CVExtraction
) -> None:
    """Compétences : référentiel global (get-or-create) + liaison N-N."""
    wanted = [(name, SkillType.hard) for name in normalize_skills(ex.hard_skills)] + [
        (name, SkillType.soft) for name in normalize_skills(ex.soft_skills)
    ]
    for name, skill_type in wanted:
        clipped = _clip(name, 255)
        if not clipped:
            continue
        skill = await _get_or_create_skill(session, clipped, skill_type)
        session.add(CandidateSkill(candidate_id=candidate_id, skill_id=skill.id))


async def _get_or_create_skill(session: AsyncSession, name: str, skill_type: SkillType) -> Skill:
    existing = (
        await session.execute(select(Skill).where(Skill.name == name, Skill.type == skill_type))
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    skill = Skill(name=name, type=skill_type)
    session.add(skill)
    await session.flush()
    return skill


async def _persist_embedding(
    session: AsyncSession,
    candidate: Candidate,
    embeddings: EmbeddingProvider,
) -> None:
    vector = (await embeddings.embed_documents([candidate.search_text or ""]))[0]
    session.add(
        CandidateEmbedding(
            candidate_id=candidate.id,
            embedding=vector,
            model_name=embeddings.__class__.__name__,
        )
    )


def _searchable_text(candidate: Candidate, ex: CVExtraction) -> str:
    parts: list[str | None] = [
        candidate.prenom,
        candidate.nom,
        candidate.poste_actuel,
        candidate.specialite,
        candidate.secteur,
        candidate.ville,
        *ex.hard_skills,
        *ex.soft_skills,
    ]
    for e in ex.experiences:
        parts += [e.poste, e.entreprise, e.description]
    for f in ex.formations:
        parts += [f.diplome, f.ecole]
    return " ".join(p for p in parts if p)


def _parse_year(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"(\d{4})", str(value))
    return int(match.group(1)) if match else None


def _parse_language(raw: str) -> tuple[str, str | None]:
    """« Français (natif) » -> ('Français', 'natif')."""
    raw = (raw or "").strip()
    match = re.match(r"^(.*?)\s*\((.*)\)\s*$", raw)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return raw, None
