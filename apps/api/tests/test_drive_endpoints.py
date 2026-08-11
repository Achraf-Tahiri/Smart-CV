"""Tests des endpoints admin de synchro Drive (RBAC + enqueue + état)."""

import pytest

from app.models.enums import UserRole
from tests.conftest import login

pytestmark = pytest.mark.anyio


@pytest.fixture
def enqueue_spy(monkeypatch):
    """Remplace `enqueue_drive_sync` : aucun Redis requis en test."""
    calls: list[str] = []

    async def fake(folder_id: str) -> None:
        calls.append(folder_id)

    monkeypatch.setattr("app.api.routes.drive.enqueue_drive_sync", fake)
    return calls


async def _admin(client, make_user):
    _, pwd = await make_user(email="admin@example.com", role=UserRole.admin)
    return await login(client, "admin@example.com", pwd)


async def _recruteur(client, make_user):
    _, pwd = await make_user(email="rec@example.com", role=UserRole.recruteur)
    return await login(client, "rec@example.com", pwd)


async def test_sync_requires_admin(client, make_user, enqueue_spy):
    headers = await _recruteur(client, make_user)
    resp = await client.post("/api/v1/drive/sync", json={"folder_id": "fld"}, headers=headers)
    assert resp.status_code == 403
    assert enqueue_spy == []


async def test_sync_requires_folder_id(client, make_user, enqueue_spy):
    headers = await _admin(client, make_user)
    resp = await client.post("/api/v1/drive/sync", json={}, headers=headers)
    assert resp.status_code == 400
    assert enqueue_spy == []


async def test_sync_enqueues_and_returns_202(client, make_user, enqueue_spy):
    headers = await _admin(client, make_user)
    resp = await client.post("/api/v1/drive/sync", json={"folder_id": "fld-123"}, headers=headers)
    assert resp.status_code == 202
    body = resp.json()
    assert body["folder_id"] == "fld-123"
    assert body["status"] == "queued"
    assert enqueue_spy == ["fld-123"]


async def test_sync_state_empty_when_never_synced(client, make_user, enqueue_spy):
    headers = await _admin(client, make_user)
    resp = await client.get("/api/v1/drive/sync-state?folder_id=fld-x", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["folder_id"] == "fld-x"
    assert body["last_sync_at"] is None


async def test_sync_state_requires_admin(client, make_user):
    headers = await _recruteur(client, make_user)
    resp = await client.get("/api/v1/drive/sync-state?folder_id=fld", headers=headers)
    assert resp.status_code == 403
