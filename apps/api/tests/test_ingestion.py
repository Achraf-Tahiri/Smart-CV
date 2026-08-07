"""Tests du pipeline d'ingestion (extraction texte réelle + LLM simulé)."""

import io
import uuid

import pytest
from docx import Document as DocxDocument
from sqlalchemy import func, select

from app.models.candidate import Candidate
from app.models.embedding import CandidateEmbedding
from app.models.enums import UserRole
from app.models.experience import Education, Experience
from app.models.job import ImportJob
from app.models.skill import CandidateLanguage, CandidateSkill, Skill
from app.providers.llm import get_llm
from app.providers.llm.fake import FakeLLMProvider
from tests.conftest import login

pytestmark = pytest.mark.anyio

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

EXTRACTION = {
    "prenom": "alex",
    "nom": "exemple",
    "email": "alex@example.com",
    "telephone": "+212600000000",
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
        {"titre": "Président", "organisation": "Association Démo", "date_debut": "2018", "date_fin": "2019"}
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


async def test_process_document_full_pipeline(app, client, make_user, db_session):
    app.dependency_overrides[get_llm] = lambda: FakeLLMProvider(EXTRACTION)
    headers = await _recruteur_headers(client, make_user)
    up = await _upload(client, headers)
    cid = uuid.UUID(up["candidate_id"])

    resp = await client.post(f"/api/v1/documents/{up['document_id']}/process", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["prenom"] == "Alex"  # format_title appliqué
    assert body["nom"] == "Exemple"
    assert body["ville"] == "Casablanca"  # quartier -> ville
    assert body["secteur"] == "Informatique / Tech"
    assert body["annees_experience"] > 0
    assert body["seniorite"]

    assert await _count(db_session, Experience, cid) == 1
    assert await _count(db_session, Education, cid) == 1
    assert await _count(db_session, CandidateLanguage, cid) == 2
    assert (
        await _count(db_session, CandidateSkill, cid) == 3
    )  # py->Python, Docker, autonome->Autonomie

    assert await db_session.get(CandidateEmbedding, cid) is not None
    python_skill = (
        await db_session.execute(select(Skill).where(Skill.name == "Python"))
    ).scalar_one_or_none()
    assert python_skill is not None  # alias 'py' normalisé

    jobs = (
        (await db_session.execute(select(ImportJob).where(ImportJob.candidate_id == cid)))
        .scalars()
        .all()
    )
    assert any(j.status.value == "success" for j in jobs)


async def test_process_is_idempotent(app, client, make_user, db_session):
    app.dependency_overrides[get_llm] = lambda: FakeLLMProvider(EXTRACTION)
    headers = await _recruteur_headers(client, make_user)
    up = await _upload(client, headers)
    cid = uuid.UUID(up["candidate_id"])

    await client.post(f"/api/v1/documents/{up['document_id']}/process", headers=headers)
    await client.post(f"/api/v1/documents/{up['document_id']}/process", headers=headers)

    assert await _count(db_session, Experience, cid) == 1  # pas de doublon


async def test_process_failure_sets_manual_review(app, client, make_user, db_session):
    app.dependency_overrides[get_llm] = lambda: FakeLLMProvider(fail=True)
    headers = await _recruteur_headers(client, make_user)
    up = await _upload(client, headers)

    resp = await client.post(f"/api/v1/documents/{up['document_id']}/process", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "manual_review"

    candidate = await db_session.get(Candidate, uuid.UUID(up["candidate_id"]))
    assert candidate.status.value == "manual_review"


async def test_process_requires_writer_role(client, make_user):
    _, pwd = await make_user(email="lecteur@example.com", role=UserRole.lecteur)
    headers = await login(client, "lecteur@example.com", pwd)
    resp = await client.post(f"/api/v1/documents/{uuid.uuid4()}/process", headers=headers)
    assert resp.status_code == 403
