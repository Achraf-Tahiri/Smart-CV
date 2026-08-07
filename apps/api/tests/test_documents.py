"""Tests d'upload / téléchargement de documents (dédup, RBAC, stockage)."""

import uuid

import pytest
from sqlalchemy import func, select

from app.models.candidate import Candidate
from app.models.enums import UserRole
from tests.conftest import login

pytestmark = pytest.mark.anyio

PDF_BYTES = b"%PDF-1.4 contenu de test"


async def _headers(client, make_user, role: UserRole):
    email = f"{role.value}@example.com"
    _, pwd = await make_user(email=email, role=role)
    return await login(client, email, pwd)


def _pdf(name: str = "cv.pdf", data: bytes = PDF_BYTES):
    return {"file": (name, data, "application/pdf")}


async def test_upload_requires_auth(client):
    resp = await client.post("/api/v1/documents/upload", files=_pdf())
    assert resp.status_code == 401


async def test_lecteur_cannot_upload(client, make_user):
    h = await _headers(client, make_user, UserRole.lecteur)
    resp = await client.post("/api/v1/documents/upload", files=_pdf(), headers=h)
    assert resp.status_code == 403


async def test_upload_creates_candidate_and_stores_file(
    client, make_user, db_session, fake_storage
):
    h = await _headers(client, make_user, UserRole.recruteur)
    resp = await client.post("/api/v1/documents/upload", files=_pdf(), headers=h)
    assert resp.status_code == 201
    body = resp.json()
    assert body["deduplicated"] is False
    assert body["filename"] == "cv.pdf"
    assert len(body["file_hash"]) == 64  # sha-256 hex

    # Le binaire est bien dans le stockage, à la clé attendue.
    assert await fake_storage.exists(f"documents/{body['document_id']}")

    # Un candidat a été créé, au statut pending (à traiter par le pipeline IA).
    candidate = await db_session.get(Candidate, uuid.UUID(body["candidate_id"]))
    assert candidate is not None
    assert candidate.status.value == "pending"


async def test_upload_same_file_is_deduplicated(client, make_user, db_session):
    h = await _headers(client, make_user, UserRole.recruteur)
    first = (await client.post("/api/v1/documents/upload", files=_pdf(), headers=h)).json()
    second = (await client.post("/api/v1/documents/upload", files=_pdf(), headers=h)).json()

    assert second["deduplicated"] is True
    assert second["document_id"] == first["document_id"]
    assert second["candidate_id"] == first["candidate_id"]

    total = await db_session.scalar(select(func.count()).select_from(Candidate))
    assert total == 1  # pas de doublon créé


async def test_upload_rejects_unsupported_extension(client, make_user):
    h = await _headers(client, make_user, UserRole.recruteur)
    resp = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("virus.exe", b"MZ", "application/octet-stream")},
        headers=h,
    )
    assert resp.status_code == 400


async def test_upload_rejects_empty_file(client, make_user):
    h = await _headers(client, make_user, UserRole.recruteur)
    resp = await client.post("/api/v1/documents/upload", files=_pdf(data=b""), headers=h)
    assert resp.status_code == 400


async def test_download_url_returned(client, make_user):
    h = await _headers(client, make_user, UserRole.recruteur)
    doc_id = (await client.post("/api/v1/documents/upload", files=_pdf(), headers=h)).json()[
        "document_id"
    ]
    resp = await client.get(f"/api/v1/documents/{doc_id}/download-url", headers=h)
    assert resp.status_code == 200
    assert resp.json()["url"].startswith("memory://documents/")
    assert resp.json()["expires_in"] == 3600


async def test_download_url_missing_document(client, make_user):
    h = await _headers(client, make_user, UserRole.recruteur)
    resp = await client.get(f"/api/v1/documents/{uuid.uuid4()}/download-url", headers=h)
    assert resp.status_code == 404
