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


# --- Refresh tokens (Phase 5c) ---


async def test_login_returns_refresh_token(client, make_user):
    await make_user(email="rt@example.com", password="password123")
    resp = await client.post(
        "/api/v1/auth/login", data={"username": "rt@example.com", "password": "password123"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["refresh_token"]
    assert body["refresh_token"] != body["access_token"]


async def test_refresh_issues_new_access_token(client, make_user):
    await make_user(email="rt2@example.com", password="password123")
    login_resp = await client.post(
        "/api/v1/auth/login", data={"username": "rt2@example.com", "password": "password123"}
    )
    old = login_resp.json()

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old["refresh_token"]})
    assert resp.status_code == 200
    body = resp.json()
    # Le refresh token change toujours (rotation). L'access token, lui, est un JWT
    # signé sur `iat`/`exp` en secondes : deux émissions dans la même seconde sont
    # identiques par construction, donc on ne compare pas son contenu ici.
    assert body["access_token"]
    assert body["refresh_token"] != old["refresh_token"]

    # Le nouvel access token est utilisable.
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200


async def test_refresh_rotation_rejects_reused_token(client, make_user):
    await make_user(email="rt3@example.com", password="password123")
    login_resp = await client.post(
        "/api/v1/auth/login", data={"username": "rt3@example.com", "password": "password123"}
    )
    old = login_resp.json()

    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": old["refresh_token"]})
    assert first.status_code == 200

    # Rejeu de l'ancien refresh token (déjà utilisé/révoqué par la rotation) : refusé.
    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": old["refresh_token"]})
    assert replay.status_code == 401


async def test_refresh_with_invalid_token_rejected(client):
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "n-importe-quoi"})
    assert resp.status_code == 401


async def test_refresh_with_revoked_user_rejected(client, db_session, make_user):
    user, password = await make_user(email="rt4@example.com", password="password123")
    login_resp = await client.post(
        "/api/v1/auth/login", data={"username": "rt4@example.com", "password": password}
    )
    refresh_token = login_resp.json()["refresh_token"]

    user.is_active = False
    db_session.add(user)
    await db_session.commit()

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 401


async def test_logout_revokes_refresh_token(client, make_user):
    await make_user(email="rt5@example.com", password="password123")
    login_resp = await client.post(
        "/api/v1/auth/login", data={"username": "rt5@example.com", "password": "password123"}
    )
    refresh_token = login_resp.json()["refresh_token"]

    logout_resp = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout_resp.status_code == 204

    # Le refresh token révoqué ne permet plus de rafraîchir.
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 401


async def test_logout_is_idempotent_on_unknown_token(client):
    resp = await client.post("/api/v1/auth/logout", json={"refresh_token": "inconnu"})
    assert resp.status_code == 204


async def test_refresh_and_logout_write_audit_log(client, db_session, make_user):
    await make_user(email="rt6@example.com", password="password123")
    login_resp = await client.post(
        "/api/v1/auth/login", data={"username": "rt6@example.com", "password": "password123"}
    )
    refresh_token = login_resp.json()["refresh_token"]

    refreshed = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    new_refresh_token = refreshed.json()["refresh_token"]
    await client.post("/api/v1/auth/logout", json={"refresh_token": new_refresh_token})

    actions = (await db_session.execute(select(AuditLog.action))).scalars().all()
    assert "refresh" in actions
    assert "logout" in actions


async def test_login_rate_limited_after_too_many_failures(app, client, make_user):
    from app.core.ratelimit import InMemoryRateLimiter, get_login_rate_limiter

    limiter = InMemoryRateLimiter(max_attempts=3)  # instance partagée entre les requêtes
    app.dependency_overrides[get_login_rate_limiter] = lambda: limiter
    await make_user(email="rl@example.com", password="password123")

    for _ in range(3):
        resp = await client.post(
            "/api/v1/auth/login", data={"username": "rl@example.com", "password": "faux"}
        )
        assert resp.status_code == 401

    # Bloqué ensuite, même avec le bon mot de passe.
    blocked = await client.post(
        "/api/v1/auth/login", data={"username": "rl@example.com", "password": "password123"}
    )
    assert blocked.status_code == 429
