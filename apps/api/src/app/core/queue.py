"""File de jobs Arq (Redis) : connexion + mise en file depuis l'API."""

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config import settings


def redis_settings() -> RedisSettings:
    """Paramètres Redis dérivés de REDIS_URL."""
    return RedisSettings.from_dsn(settings.redis_url)


_pool: ArqRedis | None = None


async def get_pool() -> ArqRedis:
    """Pool Arq partagé (créé à la première utilisation)."""
    global _pool
    if _pool is None:
        _pool = await create_pool(redis_settings())
    return _pool


async def enqueue_process_document(document_id: str) -> None:
    """Met en file le traitement IA d'un document."""
    pool = await get_pool()
    await pool.enqueue_job("process_document_task", document_id)


async def enqueue_drive_sync(folder_id: str) -> None:
    """Met en file une synchro Google Drive (folder Drive → catalogue + ingestion)."""
    pool = await get_pool()
    await pool.enqueue_job("sync_drive_folder_task", folder_id)
