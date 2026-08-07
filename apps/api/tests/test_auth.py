"""Tests de l'authentification et du contrôle de rôle."""

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.deps import require_role
from app.models.audit import AuditLog
from app.models.enums import UserRole
from app.models.user import User
from tests.conftest import login

pytestmark = pytest.mark.anyio


async def test_login_success_and_me(client, make_user):
    user, password = await make_user(email="admin@example.com", role=UserRole.admin)

    resp = await client.post(
        "/api/v1/auth/login", data={"username": "admin@example.com", "password": password}
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert resp.json()["token_type"] == "bearer"

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "admin@example.com"
    assert me.json()["role"] == "admin"
    assert "hashed_password" not in me.json()  # jamais exposé


async def test_login_wrong_password(client, make_user):
    await make_user(email="user@example.com", password="password123")
    resp = await client.post(
        "/api/v1/auth/login", data={"username": "user@example.com", "password": "mauvais"}
    )
    assert resp.status_code == 401


async def test_login_unknown_email(client):
    resp = await client.post(
        "/api/v1/auth/login", data={"username": "inconnu@example.com", "password": "xxxxxxxx"}
    )
    assert resp.status_code == 401


async def test_login_inactive_user(client, db_session, make_user):
    user, password = await make_user(email="off@example.com", password="password123")
    user.is_active = False
    db_session.add(user)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/login", data={"username": "off@example.com", "password": password}
    )
    assert resp.status_code == 401


async def test_me_requires_valid_token(client):
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    bad = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer n-importe-quoi"})
    assert bad.status_code == 401


async def test_login_writes_audit_log(client, db_session, make_user):
    await make_user(email="trace@example.com", password="password123")

    await login(client, "trace@example.com", "password123")
    await client.post(
        "/api/v1/auth/login", data={"username": "trace@example.com", "password": "faux"}
    )

    actions = (await db_session.execute(select(AuditLog.action))).scalars().all()
    assert "login" in actions
    assert "login_failed" in actions


async def test_email_is_normalized_lowercase(client, make_user):
    # Créé en minuscules, connexion avec une casse différente doit marcher.
    await make_user(email="mixed@example.com", password="password123")
    resp = await client.post(
        "/api/v1/auth/login", data={"username": "MiXeD@Example.Com", "password": "password123"}
    )
    assert resp.status_code == 200


# --- RBAC : test unitaire du fabricant de dépendance (sans HTTP) ---


def _fake_user(role: UserRole) -> User:
    return User(email="x@example.com", hashed_password="x", role=role, is_active=True)


def test_require_role_allows_listed_role():
    checker = require_role(UserRole.recruteur)
    user = _fake_user(UserRole.recruteur)
    assert checker(user) is user


def test_require_role_always_allows_admin():
    checker = require_role(UserRole.recruteur)  # admin non listé mais toujours autorisé
    admin = _fake_user(UserRole.admin)
    assert checker(admin) is admin


def test_require_role_forbids_other_roles():
    checker = require_role(UserRole.recruteur)
    lecteur = _fake_user(UserRole.lecteur)
    with pytest.raises(HTTPException) as exc:
        checker(lecteur)
    assert exc.value.status_code == 403
