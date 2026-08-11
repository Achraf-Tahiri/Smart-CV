"""Schémas RGPD : export des données d'un candidat + aperçu de la purge.

- `CandidateExport` : droit d'accès — toutes les données personnelles d'un
  candidat (identité + parcours + compétences + langues + documents + sortie
  brute d'extraction), réutilisant les schémas de fiche détaillée existants.
- `PurgePreview` : droit à l'effacement — liste (dry-run) des candidats qui
  SERAIENT purgés selon la politique de rétention, sans rien supprimer.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.candidate import CandidateDetail


class CandidateExport(CandidateDetail):
    """Export RGPD complet d'un candidat (droit d'accès).

    Étend la fiche détaillée avec la sortie brute d'extraction (`raw_extraction`)
    et des métadonnées de traçabilité de l'export.
    """

    raw_extraction: dict | None = None
    exported_at: datetime
    exported_by: str  # email de l'administrateur ayant demandé l'export


class PurgePreviewItem(BaseModel):
    """Un candidat éligible à la purge (aperçu, non supprimé)."""

    id: uuid.UUID
    nom: str | None
    prenom: str | None
    email: str | None
    created_at: datetime
    age_days: int


class PurgePreview(BaseModel):
    """Aperçu (dry-run) de la purge par rétention : ce qui SERAIT supprimé."""

    enabled: bool  # False si RETENTION_DAYS <= 0 (purge désactivée)
    retention_days: int
    cutoff: datetime | None  # date limite : les candidats plus anciens sont éligibles
    batch_limit: int  # nombre max supprimé par exécution (borne de sécurité)
    total: int  # nombre total d'éligibles (peut dépasser batch_limit)
    items: list[PurgePreviewItem]  # échantillon borné par batch_limit
