"""Tests RGPD (Phase 5) : export par candidat + rétention/purge.

Couvre :
- l'export admin (contenu complet + audit) et sa garde RBAC ;
- l'aperçu (dry-run) de la purge et sa garde RBAC ;
- la logique de purge (éligibilité par ancienneté, exclusion des CV du POC,
  désactivation par défaut, borne de lot, cascade, audit).
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.models.audit import AuditLog
from app.models.candidate import Candidate, Document
from app.models.enums import CandidateStatus, Source, UserRole
from app.models.experience import Experience
from app.models.skill import CandidateLanguage
from app.services import gdpr
from tests.conftest import login

pytestmark = pytest.mark.anyio


async def _headers(client, make_user, role: UserRole):
    email = f"{role.value}@example.com"
    _, pwd = await make_user(email=email, role=role)
    return await login(client, email, pwd)


async def _add_candidate(
    session,
    *,
    nom: str = "Test",
    prenom: str = "User",
    days_old: int = 0,
    raw_extraction: dict | None = None,
) -> Candidate:
    """Insère un candidat avec un âge (created_at) et un raw_extraction contrôlés."""
    candidate = Candidate(
        id=uuid.uuid4(),
        nom=nom,
        prenom=prenom,
        email=f"{prenom}.{nom}@example.com".lower(),
        source=Source.local,
        status=CandidateStatus.success,
        raw_extraction=raw_extraction,
        created_at=datetime.now(UTC) - timedelta(days=days_old),
    )
    session.add(candidate)
    await session.flush()
    return candidate


# --------------------------------------------------------------------------- #
# A) Export RGPD
# --------------------------------------------------------------------------- #
async def test_admin_export_returns_full_data_and_audits(client, make_user, db_session):
    h = await _headers(client, make_user, UserRole.admin)
    candidate = await _add_candidate(
        db_session, nom="Exemple", prenom="Alex", raw_extraction={"_source": "cv", "foo": "bar"}
    )
    db_session.add(Experience(candidate_id=candidate.id, poste="Dev", entreprise="ACME"))
    db_session.add(CandidateLanguage(candidate_id=candidate.id, name="Français", level="natif"))
    db_session.add(
        Document(
            candidate_id=candidate.id,
            storage_key="k",
            filename="cv.pdf",
            content_type="application/pdf",
            source=Source.local,
        )
    )
    await db_session.commit()

    resp = await client.get(f"/api/v1/gdpr/candidates/{candidate.id}/export", headers=h)
    assert resp.status_code == 200
    body = resp.json()
    assert body["nom"] == "Exemple"
    assert body["raw_extraction"]["foo"] == "bar"
    assert body["exported_by"] == "admin@example.com"
    assert "exported_at" in body
    assert [e["poste"] for e in body["experiences"]] == ["Dev"]
    assert [x["name"] for x in body["langues"]] == ["Français"]
    assert [d["filename"] for d in body["documents"]] == ["cv.pdf"]

    # Une entrée d'audit `gdpr.export` a été écrite pour ce candidat.
    total = await db_session.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(AuditLog.action == "gdpr.export", AuditLog.entity_id == candidate.id)
    )
    assert total == 1


async def test_export_forbidden_for_non_admin(client, make_user, db_session):
    h = await _headers(client, make_user, UserRole.recruteur)
    candidate = await _add_candidate(db_session)
    await db_session.commit()
    resp = await client.get(f"/api/v1/gdpr/candidates/{candidate.id}/export", headers=h)
    assert resp.status_code == 403


async def test_export_missing_returns_404(client, make_user):
    h = await _headers(client, make_user, UserRole.admin)
    resp = await client.get(f"/api/v1/gdpr/candidates/{uuid.uuid4()}/export", headers=h)
    assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# B1) Aperçu (dry-run) via l'endpoint
# --------------------------------------------------------------------------- #
async def test_preview_disabled_by_default(client, make_user):
    """RETENTION_DAYS=0 (défaut prudent) => purge désactivée, aucun éligible."""
    h = await _headers(client, make_user, UserRole.admin)
    resp = await client.get("/api/v1/gdpr/retention/preview", headers=h)
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is False
    assert body["total"] == 0
    assert body["cutoff"] is None


async def test_preview_lists_eligible_when_enabled(client, make_user, db_session, monkeypatch):
    h = await _headers(client, make_user, UserRole.admin)
    await _add_candidate(db_session, nom="Vieux", days_old=400)
    await _add_candidate(db_session, nom="Recent", days_old=10)
    await db_session.commit()

    monkeypatch.setattr(settings, "retention_days", 365)
    resp = await client.get("/api/v1/gdpr/retention/preview", headers=h)
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is True
    assert body["total"] == 1
    assert [i["nom"] for i in body["items"]] == ["Vieux"]


async def test_preview_forbidden_for_non_admin(client, make_user):
    h = await _headers(client, make_user, UserRole.recruteur)
    resp = await client.get("/api/v1/gdpr/retention/preview", headers=h)
    assert resp.status_code == 403


# --------------------------------------------------------------------------- #
# B2) Logique de purge (service)
# --------------------------------------------------------------------------- #
async def test_purge_disabled_deletes_nothing(db_session):
    await _add_candidate(db_session, days_old=1000)
    await db_session.commit()
    purged = await gdpr.purge_expired_candidates(db_session, retention_days=0, batch_limit=100)
    assert purged == []
    assert await db_session.scalar(select(func.count()).select_from(Candidate)) == 1


async def test_purge_respects_age_and_protects_poc(db_session):
    old = await _add_candidate(db_session, nom="Old", days_old=400)
    await _add_candidate(db_session, nom="Recent", days_old=5)
    # CV migré du POC : ancien MAIS marqué `_poc_id` => sanctuarisé.
    poc = await _add_candidate(db_session, nom="POC", days_old=999, raw_extraction={"_poc_id": 42})
    await db_session.commit()

    purged = await gdpr.purge_expired_candidates(db_session, retention_days=365, batch_limit=100)
    await db_session.commit()

    assert [p["nom"] for p in purged] == ["Old"]
    remaining = set((await db_session.execute(select(Candidate.id))).scalars().all())
    assert old.id not in remaining
    assert poc.id in remaining  # POC jamais purgé
    assert len(remaining) == 2

    # Un audit `candidate.purge` par candidat supprimé.
    audits = await db_session.scalar(
        select(func.count()).select_from(AuditLog).where(AuditLog.action == "candidate.purge")
    )
    assert audits == 1


async def test_purge_cascade_removes_children(db_session):
    candidate = await _add_candidate(db_session, nom="WithChildren", days_old=500)
    db_session.add(Experience(candidate_id=candidate.id, poste="Dev"))
    db_session.add(CandidateLanguage(candidate_id=candidate.id, name="Anglais"))
    await db_session.commit()

    await gdpr.purge_expired_candidates(db_session, retention_days=100, batch_limit=100)
    await db_session.commit()

    exp = await db_session.scalar(select(func.count()).select_from(Experience))
    langs = await db_session.scalar(select(func.count()).select_from(CandidateLanguage))
    assert exp == 0
    assert langs == 0


async def test_purge_batch_limit_bounds_deletions(db_session):
    for i in range(4):
        await _add_candidate(db_session, nom=f"Old{i}", days_old=400)
    await db_session.commit()

    purged = await gdpr.purge_expired_candidates(db_session, retention_days=365, batch_limit=2)
    await db_session.commit()
    assert len(purged) == 2
    # Il reste 2 éligibles pour la prochaine exécution.
    assert await db_session.scalar(select(func.count()).select_from(Candidate)) == 2


async def test_preview_counts_total_beyond_batch_limit(db_session):
    for i in range(5):
        await _add_candidate(db_session, nom=f"Old{i}", days_old=400)
    await db_session.commit()

    preview = await gdpr.preview_purge(db_session, retention_days=365, batch_limit=2)
    assert preview.total == 5  # total réel
    assert len(preview.items) == 2  # échantillon borné
