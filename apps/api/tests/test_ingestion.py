"""Tests du pipeline d'ingestion (appelé directement) et de sa mise en file.

Le pipeline (`ingestion.process_document`) est testé en direct — c'est la même
fonction que le worker exécute. L'endpoint, lui, ne fait plus que **mettre en
file** (asynchrone) : on vérifie l'enqueue, pas le traitement.
"""

import io
import uuid

import pytest
from docx import Document as DocxDocument
from sqlalchemy import func, select

from app.models.candidate import Document
from app.models.embedding import CandidateEmbedding
from app.models.enums import UserRole
from app.models.experience import Experience
from app.models.skill import CandidateLanguage, CandidateSkill, Skill
from app.providers.embeddings.deterministic import DeterministicEmbeddingProvider
from app.providers.llm.fake import FakeLLMProvider
from app.services import ingestion
from tests.conftest import login

pytestmark = pytest.mark.anyio

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_EMB = DeterministicEmbeddingProvider(768)

EXTRACTION = {
    "prenom": "alex",
    "nom": "exemple",
    "email": "alex@example.com",
    "ville": "Sidi Bernoussi, Casablanca",
    "poste_actuel": "data scientist",
    "secteur": "Informatique / Tech",
    "specialite": "Data Science",
    "experiences": [
        {
            "poste": "Data Scientist",
            "entreprise": "ACME",
            "date_debut": "2020-01",
            "date_fin": "PRESENT",
            "description": "ML",
        }
    ],
    "formations": [{"diplome": "Ingénieur", "ecole": "Institut Exemple", "annee": "2019"}],
    "activites_extra": [
        {
            "titre": "Président",
            "organisation": "Association Démo",
            "date_debut": "2018",
            "date_fin": "2019",
        }
    ],
    "hard_skills": ["py", "Docker"],
    "soft_skills": ["autonome"],
    "langues": ["Français (natif)", "Anglais (courant)"],
}


def _docx_bytes(text: str = "Alex Exemple\nData Scientist chez ACME\nPython Docker") -> bytes:
    doc = DocxDocument()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


async def _recruteur_headers(client, make_user):
    _, pwd = await make_user(email="recruteur@example.com", role=UserRole.recruteur)
    return await login(client, "recruteur@example.com", pwd)


async def _upload(client, headers) -> dict:
    resp = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("cv.docx", _docx_bytes(), _DOCX_MIME)},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


async def _count(db_session, model, candidate_id) -> int:
    return await db_session.scalar(
        select(func.count()).select_from(model).where(model.candidate_id == candidate_id)
    )


async def _run_pipeline(db_session, document_id: str, fake_storage, *, fail: bool = False):
    """Exécute le pipeline exactement comme le worker (mais en direct, testable)."""
    document = await db_session.get(Document, uuid.UUID(document_id))
    candidate = await ingestion.process_document(
        db_session,
        document=document,
        llm=FakeLLMProvider(EXTRACTION, fail=fail),
        embeddings=_EMB,
        storage=fake_storage,
    )
    await db_session.commit()
    return candidate


async def test_pipeline_full(app, client, make_user, db_session, fake_storage):
    headers = await _recruteur_headers(client, make_user)
    up = await _upload(client, headers)
    cid = uuid.UUID(up["candidate_id"])

    candidate = await _run_pipeline(db_session, up["document_id"], fake_storage)
    assert candidate.status.value == "success"
    assert candidate.prenom == "Alex"  # format_title
    assert candidate.ville == "Casablanca"  # quartier -> ville
    assert candidate.annees_experience > 0

    assert await _count(db_session, Experience, cid) == 1
    assert await _count(db_session, CandidateLanguage, cid) == 2
    assert (
        await _count(db_session, CandidateSkill, cid) == 3
    )  # py->Python, Docker, autonome->Autonomie
    assert await db_session.get(CandidateEmbedding, cid) is not None
    python_skill = (
        await db_session.execute(select(Skill).where(Skill.name == "Python"))
    ).scalar_one_or_none()
    assert python_skill is not None


async def test_pipeline_idempotent(app, client, make_user, db_session, fake_storage):
    headers = await _recruteur_headers(client, make_user)
    up = await _upload(client, headers)
    cid = uuid.UUID(up["candidate_id"])

    await _run_pipeline(db_session, up["document_id"], fake_storage)
    await _run_pipeline(db_session, up["document_id"], fake_storage)

    assert await _count(db_session, Experience, cid) == 1  # pas de doublon


async def test_pipeline_failure_sets_manual_review(
    app, client, make_user, db_session, fake_storage
):
    headers = await _recruteur_headers(client, make_user)
    up = await _upload(client, headers)
    candidate = await _run_pipeline(db_session, up["document_id"], fake_storage, fail=True)
    assert candidate.status.value == "manual_review"


async def test_detail_exposes_nested_data_after_pipeline(
    app, client, make_user, db_session, fake_storage
):
    headers = await _recruteur_headers(client, make_user)
    up = await _upload(client, headers)
    await _run_pipeline(db_session, up["document_id"], fake_storage)

    detail = await client.get(f"/api/v1/candidates/{up['candidate_id']}", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert len(body["experiences"]) == 1
    assert len(body["skills"]) == 3
    assert len(body["langues"]) == 2
    assert len(body["documents"]) == 1


async def test_process_endpoint_enqueues(app, client, make_user, monkeypatch):
    calls: list[str] = []

    async def fake_enqueue(document_id: str) -> None:
        calls.append(document_id)

    monkeypatch.setattr("app.api.routes.documents.enqueue_process_document", fake_enqueue)

    headers = await _recruteur_headers(client, make_user)
    up = await _upload(client, headers)
    resp = await client.post(f"/api/v1/documents/{up['document_id']}/process", headers=headers)

    assert resp.status_code == 202
    assert resp.json()["status"] == "pending"  # sera traité par le worker
    assert calls == [up["document_id"]]


async def test_process_requires_writer_role(client, make_user):
    _, pwd = await make_user(email="lecteur@example.com", role=UserRole.lecteur)
    headers = await login(client, "lecteur@example.com", pwd)
    resp = await client.post(f"/api/v1/documents/{uuid.uuid4()}/process", headers=headers)
    assert resp.status_code == 403


async def test_apply_extraction_clips_overlong_values(db_session):
    """Des valeurs anormalement longues (LLM/POC) ne doivent pas casser l'insertion."""
    from app.models.candidate import Candidate
    from app.models.enums import Source
    from app.schemas.extraction import CVExtraction

    candidate = Candidate(id=uuid.uuid4(), source=Source.local)
    db_session.add(candidate)
    await db_session.flush()

    extraction = CVExtraction(langues=["X" * 200], hard_skills=["Y" * 300], prenom="Z" * 400)
    await ingestion.apply_extraction(db_session, candidate, extraction, _EMB)
    await db_session.commit()  # ne doit PAS lever (colonnes VARCHAR bornées)

    assert candidate.prenom is not None and len(candidate.prenom) <= 255
