"""Schémas Pydantic pour l'authentification."""

from pydantic import BaseModel


class Token(BaseModel):
    """Réponse de `POST /auth/login` (jeton d'accès JWT)."""

    access_token: str
    token_type: str = "bearer"
