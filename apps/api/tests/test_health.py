"""Tests du endpoint de santé."""

import pytest

from app.core.config import settings

# Tous les tests de ce module s'exécutent en async (via anyio).
pytestmark = pytest.mark.anyio


async def test_health_ok(client):
    """GET /health répond 200 avec les infos attendues."""
    resp = await client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["app"] == settings.app_name
    assert data["env"] == settings.app_env
    assert data["version"] == settings.version
