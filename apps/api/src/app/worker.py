"""Worker Arq : exécute le pipeline d'ingestion en tâche de fond.

Lancé par le service `worker` du docker-compose : `arq app.worker.WorkerSettings`.
Réutilise exactement la même logique que le traitement synchrone
(`services.ingestion.process_document`), mais hors du cycle requête/réponse HTTP.
"""

import uuid

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.queue import redis_settings
from app.db.session import AsyncSessionLocal
from app.models.candidate import Document
from app.providers.embeddings import get_embeddings
from app.providers.llm import get_llm
from app.providers.storage import get_storage
from app.services import ingestion

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


async def _on_startup(ctx: dict) -> None:
    configure_logging(settings.log_level, json_logs=not settings.is_local)
    logger.info("worker_started")


class WorkerSettings:
    """Configuration lue par la commande `arq`."""

    functions = [process_document_task]
    redis_settings = redis_settings()
    on_startup = _on_startup
