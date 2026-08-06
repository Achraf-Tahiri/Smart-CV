"""Endpoints de santé.

- /health     : liveness (l'API est vivante, sans dépendance externe).
- /health/db  : readiness (l'API peut joindre la base de données).

Non versionnés (pas sous /api/v1) : destinés aux orchestrateurs et load balancers.
"""

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from app.schemas.health import HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Vérifie que l'API répond")
async def health() -> HealthResponse:
    """Liveness : l'API est vivante (aucune dépendance externe testée)."""
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        env=settings.app_env,
        version=settings.version,
    )


@router.get(
    "/health/db",
    response_model=ReadinessResponse,
    summary="Vérifie la connexion à la base de données",
)
async def health_db(response: Response) -> ReadinessResponse:
    """Readiness : exécute un `SELECT 1`. Renvoie 503 si la base est injoignable."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return ReadinessResponse(status="ok", db="ok")
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(status="degraded", db="down")
