"""Schémas Pydantic — synchronisation Google Drive (Phase 3b)."""

from datetime import datetime

from pydantic import BaseModel, Field


class DriveSyncRequest(BaseModel):
    """Payload de déclenchement d'une synchro Drive.

    `folder_id` optionnel : si absent, on utilise `GOOGLE_DRIVE_FOLDER_ID` de la
    config. Explicite dans le corps > défaut d'environnement.
    """

    folder_id: str | None = Field(
        default=None, description="Identifiant du dossier Drive à synchroniser."
    )


class DriveSyncAccepted(BaseModel):
    """Réponse 202 : la synchro a été mise en file (traitée par le worker)."""

    folder_id: str
    status: str = "queued"


class DriveSyncStateRead(BaseModel):
    """État de la dernière synchro d'un dossier."""

    folder_id: str
    last_sync_at: datetime | None
    cursor: str | None = None
