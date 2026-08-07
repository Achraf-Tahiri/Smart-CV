"""Tests unitaires de la sécurité (hachage + JWT) — aucune base requise."""

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
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
