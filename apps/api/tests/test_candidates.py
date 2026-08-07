"""Tests du CRUD candidats : auth, RBAC, filtres, pagination, audit."""

import uuid

import pytest
from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.enums import UserRole
from tests.conftest import login

pytestmark = pytest.mark.anyio


async def _headers(client, make_user, role: UserRole):
    email = f"{role.value}@example.com"
    _, pwd = await make_user(email=email, role=role)
    return await login(client, email, pwd)


async def test_endpoints_require_auth(client):
    assert (await client.get("/api/v1/candidates")).status_code == 401
    assert (await client.post("/api/v1/candidates", json={})).status_code == 401


async def test_create_then_get(client, make_user):
    h = await _headers(client, make_user, UserRole.recruteur)
    resp = await client.post(
        "/api/v1/candidates",
        json={
            "prenom": "Alex",
            "nom": "Exemple",
            "secteur": "Informatique / Tech",
            "ville": "Casablanca",
            "annees_experience": 4.5,
        },
        headers=h,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["prenom"] == "Alex"
    assert body["status"] == "success"  # défaut création manuelle
    assert body["source"] == "local"

    got = await client.get(f"/api/v1/candidates/{body['id']}", headers=h)
    assert got.status_code == 200
    assert got.json()["nom"] == "Exemple"


async def test_lecteur_can_read_but_not_write(client, make_user):
    h = await _headers(client, make_user, UserRole.lecteur)
    assert (await client.get("/api/v1/candidates", headers=h)).status_code == 200
    resp = await client.post("/api/v1/candidates", json={"prenom": "X"}, headers=h)
    assert resp.status_code == 403


async def test_get_missing_returns_404(client, make_user):
    h = await _headers(client, make_user, UserRole.recruteur)
    resp = await client.get(f"/api/v1/candidates/{uuid.uuid4()}", headers=h)
    assert resp.status_code == 404


async def test_update_applies_changes_and_audits(client, make_user, db_session):
    h = await _headers(client, make_user, UserRole.recruteur)
    cid = (
        await client.post(
            "/api/v1/candidates",
            json={"prenom": "Alex", "seniorite": "Junior"},
            headers=h,
        )
    ).json()["id"]

    resp = await client.patch(
        f"/api/v1/candidates/{cid}",
        json={"seniorite": "Senior", "ville": "Rabat"},
        headers=h,
    )
    assert resp.status_code == 200
    assert resp.json()["seniorite"] == "Senior"
    assert resp.json()["ville"] == "Rabat"
    assert resp.json()["prenom"] == "Alex"  # inchangé

    actions = (await db_session.execute(select(AuditLog.action))).scalars().all()
    assert "candidate.update" in actions


async def test_delete_removes_and_audits(client, make_user, db_session):
    h = await _headers(client, make_user, UserRole.recruteur)
    cid = (
        await client.post("/api/v1/candidates", json={"prenom": "ASupprimer"}, headers=h)
    ).json()["id"]

    resp = await client.delete(f"/api/v1/candidates/{cid}", headers=h)
    assert resp.status_code == 204
    assert (await client.get(f"/api/v1/candidates/{cid}", headers=h)).status_code == 404

    actions = (await db_session.execute(select(AuditLog.action))).scalars().all()
    assert "candidate.delete" in actions


async def test_filters_and_pagination(client, make_user):
    h = await _headers(client, make_user, UserRole.recruteur)
    for d in [
        {
            "prenom": "Alpha",
            "secteur": "Informatique / Tech",
            "ville": "Casablanca",
            "annees_experience": 2,
        },
        {
            "prenom": "Beta",
            "secteur": "Finance / Banque / Assurance",
            "ville": "Rabat",
            "annees_experience": 8,
        },
        {
            "prenom": "Gamma",
            "secteur": "Informatique / Tech",
            "ville": "Casablanca",
            "annees_experience": 5,
        },
    ]:
        assert (await client.post("/api/v1/candidates", json=d, headers=h)).status_code == 201

    async def total(**params):
        r = await client.get("/api/v1/candidates", params=params, headers=h)
        assert r.status_code == 200
        return r.json()["total"]

    assert await total(secteur="Informatique / Tech") == 2
    assert await total(ville="casa") == 2  # ilike insensible à la casse
    assert await total(min_experience=5) == 2
    assert await total(max_experience=2) == 1
    assert await total(q="Alpha") == 1

    r = await client.get("/api/v1/candidates", params={"limit": 2, "offset": 0}, headers=h)
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["limit"] == 2 and body["offset"] == 0


async def test_stats(client, make_user):
    h = await _headers(client, make_user, UserRole.recruteur)
    for prenom in ("A", "B"):
        await client.post(
            "/api/v1/candidates",
            json={"prenom": prenom, "secteur": "Informatique / Tech"},
            headers=h,
        )
    resp = await client.get("/api/v1/candidates/stats", headers=h)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["by_secteur"].get("Informatique / Tech") == 2
    assert body["by_status"].get("success") == 2
