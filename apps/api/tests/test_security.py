"""Tests unitaires de la sécurité (hachage + JWT) — aucune base requise."""

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_hash_and_verify_roundtrip():
    hashed = hash_password("motdepasse-secret")
    assert hashed != "motdepasse-secret"  # jamais en clair
    assert verify_password("motdepasse-secret", hashed) is True


def test_verify_wrong_password():
    hashed = hash_password("le-bon")
    assert verify_password("le-mauvais", hashed) is False


def test_verify_invalid_hash_does_not_raise():
    # Un hash corrompu ne doit pas lever, juste renvoyer False.
    assert verify_password("peu importe", "pas-un-hash-argon2") is False


def test_token_roundtrip():
    token = create_access_token(subject="abc-123", role="admin")
    payload = decode_access_token(token)
    assert payload["sub"] == "abc-123"
    assert payload["role"] == "admin"


def test_expired_token_is_rejected():
    token = create_access_token(subject="abc-123", role="admin", expires_minutes=-1)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_tampered_token_is_rejected():
    token = create_access_token(subject="abc-123", role="admin")
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token + "corrompu")


def test_generate_refresh_token_is_unique_and_high_entropy():
    a, b = generate_refresh_token(), generate_refresh_token()
    assert a != b
    assert len(a) > 40  # secrets.token_urlsafe(64) => bien plus long qu'un mot de passe


def test_hash_refresh_token_is_deterministic_and_not_reversible():
    token = generate_refresh_token()
    assert hash_refresh_token(token) == hash_refresh_token(token)
    assert hash_refresh_token(token) != token
