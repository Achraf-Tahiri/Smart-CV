"""Tests de la consultation du journal d'audit (admin only)."""

import pytest

from app.models.enums import UserRole
from tests.conftest import login

pytestmark = pytest.mark.anyio


async def test_admin_can_list_audit_logs(client, make_user):
    _, pwd = await make_user(email="admin@example.com", role=UserRole.admin)
    headers = await login(client, "admin@example.com", pwd)  # écrit une entrée "login"

    resp = await client.get("/api/v1/audit-logs", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert "login" in [item["action"] for item in body["items"]]


async def test_audit_logs_filter_by_action(client, make_user):
    _, pwd = await make_user(email="admin@example.com", role=UserRole.admin)
    headers = await login(client, "admin@example.com", pwd)

    resp = await client.get("/api/v1/audit-logs", params={"action": "login"}, headers=headers)
    assert resp.status_code == 200
    assert all(item["action"] == "login" for item in resp.json()["items"])


async def test_audit_logs_forbidden_for_non_admin(client, make_user):
    _, pwd = await make_user(email="recruteur@example.com", role=UserRole.recruteur)
    headers = await login(client, "recruteur@example.com", pwd)

    resp = await client.get("/api/v1/audit-logs", headers=headers)
    assert resp.status_code == 403
