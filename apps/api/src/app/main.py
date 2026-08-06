"""Point d'entrée de l'API New Smart CV.

Expose une fabrique `create_app()` (utilisée par les tests) et une instance
`app` au niveau module (utilisée par uvicorn : `uvicorn app.main:app`).
"""

from fastapi import FastAPI

from app.api.router import api_router
from app.api.routes import health
from app.core.config import settings
from app.core.logging import configure_logging, get_logger


def create_app() -> FastAPI:
    """Construit et configure l'application FastAPI."""
    # Logs JSON hors local, rendu console en local.
    configure_logging(settings.log_level, json_logs=not settings.is_local)
    logger = get_logger("app")

    app = FastAPI(title=settings.app_name, version=settings.version)

    # Santé : endpoint racine, non versionné (orchestrateurs / load balancers).
    app.include_router(health.router)
    # API métier versionnée.
    app.include_router(api_router, prefix="/api/v1")

    logger.info(
        "app_started",
        app=settings.app_name,
        env=settings.app_env,
        version=settings.version,
    )
    return app


app = create_app()
