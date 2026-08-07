"""Routeur agrégateur de l'API métier versionnée (montée sous /api/v1)."""

from fastapi import APIRouter

from app.api.routes import auth

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth")
