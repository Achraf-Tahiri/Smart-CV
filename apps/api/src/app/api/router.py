"""Routeur agrégateur de l'API métier versionnée (montée sous /api/v1).

Les routers métier seront ajoutés ici en Phase 1, par exemple :

    from app.api.routes import candidates
    api_router.include_router(candidates.router, prefix="/candidates", tags=["candidates"])
"""

from fastapi import APIRouter

api_router = APIRouter()
