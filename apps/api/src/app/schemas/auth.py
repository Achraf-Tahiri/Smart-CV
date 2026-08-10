"""Schémas Pydantic pour l'authentification."""

from pydantic import BaseModel


class Token(BaseModel):
    """Réponse de `POST /auth/login` et `POST /auth/refresh`.

    `refresh_token` est un jeton opaque (non-JWT) à conserver côté client
    pour obtenir un nouvel `access_token` sans redemander le mot de passe.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Corps de `POST /auth/refresh` et `POST /auth/logout`."""

    refresh_token: str
