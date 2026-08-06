"""Schéma de réponse du endpoint de santé."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Réponse renvoyée par GET /health."""

    status: str = "ok"
    app: str
    env: str
    version: str
