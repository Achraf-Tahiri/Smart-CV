"""Routeur agrégateur de l'API métier versionnée (montée sous /api/v1)."""

from fastapi import APIRouter

from app.api.routes import audit_logs, auth, candidates, documents, drive, gdpr

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth")
api_router.include_router(candidates.router, prefix="/candidates")
api_router.include_router(documents.router, prefix="/documents")
api_router.include_router(audit_logs.router, prefix="/audit-logs")
api_router.include_router(gdpr.router, prefix="/gdpr")
api_router.include_router(drive.router, prefix="/drive")
