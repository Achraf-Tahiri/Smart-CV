"""Worker Arq : exécute le pipeline d'ingestion en tâche de fond.

Lancé par le service `worker` du docker-compose : `arq app.worker.WorkerSettings`.
Réutilise exactement la même logique que le traitement synchrone
(`services.ingestion.process_document`), mais hors du cycle requête/réponse HTTP.
"""

import uuid

from arq import cron

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.queue import redis_settings
from app.db.session import AsyncSessionLocal
from app.models.candidate import Document
from app.providers.drive import get_drive_provider
from app.providers.drive.base import DriveProviderError
from app.providers.embeddings import get_embeddings
from app.providers.llm import get_llm
from app.providers.storage import get_storage
from app.services import drive_sync, gdpr, ingestion

logger = get_logger("worker")


async def process_document_task(ctx: dict, document_id: str) -> str:
    """Tâche Arq : traite un document et met à jour le candidat associé."""
    async with AsyncSessionLocal() as session:
        document = await session.get(Document, uuid.UUID(document_id))
        if document is None:
            logger.warning("worker_document_absent", document_id=document_id)
            return "not_found"
        candidate = await ingestion.process_document(
            session,
            document=document,
            llm=get_llm(),
            embeddings=get_embeddings(),
            storage=get_storage(),
        )
        await session.commit()
        logger.info("worker_processed", document_id=document_id, status=candidate.status.value)
        return candidate.status.value


async def sync_drive_folder_task(ctx: dict, folder_id: str) -> str:
    """Tâche Arq : synchronise un dossier Drive vers le catalogue.

    Retry/backoff : géré par Arq via `max_tries` (défaut 5, borné par
    `WorkerSettings.max_tries`) et l'attribut `Retry` levé sur erreur transitoire.
    On lève `arq.jobs.Retry` avec un défer croissant (jamais un `sleep` bloquant :
    le worker reste dispo pour les autres jobs). En cas d'erreur définitive
    (auth, config), on journalise et on abandonne — pas de circuit breaker
    `sleep(600)`/`sleep(86400)` comme dans le POC.
    """
    from arq.jobs import Retry

    try:
        drive = get_drive_provider()
    except DriveProviderError as exc:
        logger.error("drive_sync_disabled", folder_id=folder_id, error=str(exc))
        return f"disabled:{exc}"

    async with AsyncSessionLocal() as session:
        try:
            result = await drive_sync.sync_drive_folder(
                session,
                folder_id=folder_id,
                drive=drive,
                storage=get_storage(),
            )
            await session.commit()
        except DriveProviderError as exc:
            await session.rollback()
            attempt = ctx.get("job_try", 1)
            defer = min(300, 15 * 2 ** (attempt - 1))  # 15s, 30s, 60s, … plafonné à 5 min
            logger.warning(
                "drive_sync_retry",
                folder_id=folder_id,
                attempt=attempt,
                defer_seconds=defer,
                error=str(exc),
            )
            raise Retry(defer=defer) from exc

    logger.info(
        "drive_sync_done",
        folder_id=folder_id,
        listed=result.listed,
        imported=result.imported,
        skipped_drive_id=result.skipped_by_drive_id,
        skipped_hash=result.skipped_by_hash,
        errors=len(result.errors),
    )
    return (
        f"listed={result.listed} imported={result.imported} "
        f"skipped_drive={result.skipped_by_drive_id} skipped_hash={result.skipped_by_hash} "
        f"errors={len(result.errors)}"
    )


async def purge_expired_candidates_task(ctx: dict) -> str:
    """Tâche cron (RGPD) : purge en cascade les candidats hors rétention.

    ⚠️ IRRÉVERSIBLE. No-op si RETENTION_DAYS <= 0 (désactivée par défaut).
    Les CV migrés du POC sont exclus par le service. Chaque suppression écrit
    une entrée d'audit `candidate.purge`.
    """
    if settings.retention_days <= 0:
        logger.info("purge_disabled", retention_days=settings.retention_days)
        return "disabled"
    async with AsyncSessionLocal() as session:
        purged = await gdpr.purge_expired_candidates(
            session,
            retention_days=settings.retention_days,
            batch_limit=settings.retention_purge_batch_limit,
            actor_id=None,  # exécution automatique (pas d'utilisateur)
        )
        await session.commit()
    logger.info(
        "purge_done",
        retention_days=settings.retention_days,
        purged=len(purged),
    )
    return f"purged={len(purged)}"


async def _on_startup(ctx: dict) -> None:
    configure_logging(settings.log_level, json_logs=not settings.is_local)
    logger.info("worker_started")


class WorkerSettings:
    """Configuration lue par la commande `arq`."""

    functions = [process_document_task, sync_drive_folder_task]
    max_tries = 5  # retries Arq (avec `Retry(defer=…)` géré au cas par cas)
    # Purge RGPD quotidienne à 03:30 (heure creuse). No-op tant que
    # RETENTION_DAYS=0 : la planification est inerte tant qu'on ne l'active pas.
    cron_jobs = [cron(purge_expired_candidates_task, hour=3, minute=30)]
    redis_settings = redis_settings()
    on_startup = _on_startup
