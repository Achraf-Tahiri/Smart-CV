"""Le front (origine différente) doit être autorisé par CORS."""

import pytest

pytestmark = pytest.mark.anyio


async def test_cors_allows_front_origin(client):
    resp = await client.get("/health", headers={"Origin": "http://localhost:3001"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3001"


async def test_cors_omits_unknown_origin(client):
    resp = await client.get("/health", headers={"Origin": "http://evil.example"})
    # Origine non autorisée -> pas d'en-tête permissif renvoyé.
    assert resp.headers.get("access-control-allow-origin") != "http://evil.example"
