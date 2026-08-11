"""Synchronisation d'un dossier Google Drive vers le catalogue de candidats.

Pipeline :
    lister Drive → dédupliquer (drive_file_id, puis hash contenu via import_document)
    → écrire l'objet dans le stockage → créer/rattacher le Document
    → mettre en file l'ingestion IA (worker Arq)
    → mettre à jour `sync_state` (curseur = last_sync_at).

Idempotent :
- un même `drive_file_id` déjà connu ⇒ **skippé** (pas de re-téléchargement) ;
- un contenu identique déjà présent (hash) ⇒ **skippé** par `import_document`,
  mais on complète les métadonnées Drive du Document existant si nécessaire.

Convention : ne commit pas (l'appelant/tâche Arq gère la transaction).
Les erreurs par fichier sont capturées (le lot continue) ; les erreurs globales
(auth, quota…) remontent pour que la tâche Arq re-tente avec backoff.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.queue import enqueue_process_document
from app.models.candidate import Document
from app.models.enums import Source
from app.models.job import SyncState
from app.providers.drive.base import DriveFile, DriveProvider, DriveProviderError
from app.providers.storage import StorageProvider
from app.services import documents as documents_service

logger = get_logger("drive_sync")


@dataclass
class DriveSyncResult:
    """Résumé d'une synchro (retourné par le service, journalisé par la tâche)."""

    folder_id: str
    listed: int = 0
    skipped_by_drive_id: int = 0
    skipped_by_hash: int = 0
    imported: int = 0
    enqueued: int = 0
    errors: list[str] = field(default_factory=list)


async def sync_drive_folder(
    session: AsyncSession,
    *,
    folder_id: str,
    drive: DriveProvider,
    storage: StorageProvider,
    created_by_id=None,
) -> DriveSyncResult:
    """Synchronise un dossier Drive. Idempotent."""
    result = DriveSyncResult(folder_id=folder_id)

    files: list[DriveFile] = await drive.list_files(folder_id)
    result.listed = len(files)

    known_drive_ids = await _known_drive_file_ids(session, [f.id for f in files])

    for meta in files:
        if meta.id in known_drive_ids:
            result.skipped_by_drive_id += 1
            continue

        try:
            data, content_type = await drive.download_file(meta.id)
        except DriveProviderError as exc:
            result.errors.append(f"{meta.id}:{exc}")
            logger.warning("drive_download_failed", file_id=meta.id, error=str(exc))
            continue

        document, created = await documents_service.import_document(
            session,
            storage,
            filename=meta.name,
            content_type=content_type or meta.mime_type or None,
            data=data,
            source=Source.google_drive,
            created_by_id=created_by_id,
        )

        # Toujours (ré)ancrer les métadonnées Drive sur le Document (nouveau OU dédupliqué).
        if document.drive_file_id is None:
            document.drive_file_id = meta.id
        if document.drive_view_url is None:
            document.drive_view_url = drive.get_view_url(meta.id)

        if created:
            result.imported += 1
            await session.flush()  # id disponible pour la mise en file
            await enqueue_process_document(str(document.id))
            result.enqueued += 1
        else:
            result.skipped_by_hash += 1

    await _update_sync_state(session, folder_id)
    return result


async def _known_drive_file_ids(session: AsyncSession, ids: list[str]) -> set[str]:
    """Retourne les drive_file_id déjà connus (dédup avant téléchargement)."""
    if not ids:
        return set()
    rows = await session.execute(
        select(Document.drive_file_id).where(Document.drive_file_id.in_(ids))
    )
    return {row[0] for row in rows.all() if row[0] is not None}


async def _update_sync_state(session: AsyncSession, folder_id: str) -> None:
    state = (
        await session.execute(select(SyncState).where(SyncState.drive_folder_id == folder_id))
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if state is None:
        session.add(SyncState(drive_folder_id=folder_id, last_sync_at=now))
    else:
        state.last_sync_at = now
    await session.flush()


async def get_sync_state(session: AsyncSession, folder_id: str) -> SyncState | None:
    """Lit l'état de synchro d'un dossier (endpoint admin)."""
    return (
        await session.execute(select(SyncState).where(SyncState.drive_folder_id == folder_id))
    ).scalar_one_or_none()
