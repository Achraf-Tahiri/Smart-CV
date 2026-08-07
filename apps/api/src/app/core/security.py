"""Sécurité : hachage de mot de passe (Argon2id) et jetons JWT.

Ce module ne contient que des fonctions pures (aucune dépendance à la base ni
à FastAPI) : il est donc simple à tester unitairement.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import settings

# Argon2id avec les paramètres par défaut de la lib (robustes et à jour).
_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Retourne le hash Argon2id d'un mot de passe en clair."""
    return _password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Vérifie qu'un mot de passe correspond à un hash. Ne lève jamais.

    Renvoie False si le mot de passe est faux (`VerificationError`) ou si le
    hash stocké est malformé (`InvalidHashError`).
    """
    try:
        return _password_hasher.verify(hashed, password)
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    """Indique si le hash doit être régénéré (paramètres Argon2 obsolètes)."""
    return _password_hasher.check_needs_rehash(hashed)


def create_access_token(
    subject: str,
    role: str,
    *,
    expires_minutes: int | None = None,
) -> str:
    """Émet un JWT d'accès signé.

    Args:
        subject: identifiant du sujet (ici l'UUID de l'utilisateur, en str).
        role: rôle de l'utilisateur (embarqué pour éviter un accès DB au décodage).
        expires_minutes: durée de validité ; défaut = config `access_token_expire_minutes`.
    """
    now = datetime.now(UTC)
    minutes = (
        expires_minutes if expires_minutes is not None else settings.access_token_expire_minutes
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Décode et vérifie un JWT. Lève `jwt.PyJWTError` si invalide ou expiré."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
