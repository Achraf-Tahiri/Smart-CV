"""Endpoint de santé (health check).

Non versionné (pas sous /api/v1) : destiné aux orchestrateurs et load balancers.
En Phase 0.4, il vérifiera aussi la connexion à la base de données.
"""

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Vérifie que l'API répond")
async def health() -> HealthResponse:
    """Retourne l'état de l'API."""
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        env=settings.app_env,
        version=settings.version,
    )
