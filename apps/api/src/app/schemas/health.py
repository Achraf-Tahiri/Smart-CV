"""Schéma de réponse du endpoint de santé."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Réponse renvoyée par GET /health (liveness)."""

    status: str = "ok"
    app: str
    env: str
    version: str


class ReadinessResponse(BaseModel):
    """Réponse renvoyée par GET /health/db (readiness)."""

    status: str
    db: str
