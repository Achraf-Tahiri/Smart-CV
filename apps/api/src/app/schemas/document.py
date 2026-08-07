"""Schémas Pydantic pour les documents (fichiers CV)."""

import uuid

from pydantic import BaseModel


class DocumentUploadResult(BaseModel):
    """Résultat d'un upload de document."""

    candidate_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    file_hash: str
    # True si le fichier existait déjà (déduplication par hash) : rien n'a été recréé.
    deduplicated: bool


class DownloadUrl(BaseModel):
    """URL signée temporaire de téléchargement."""

    url: str
    expires_in: int
