"""Fournisseur de stockage d'objets — point d'entrée + injection FastAPI."""

from functools import lru_cache

from app.providers.storage.base import StorageProvider
from app.providers.storage.s3 import S3StorageProvider

__all__ = ["StorageProvider", "get_storage"]


@lru_cache
def _default_storage() -> S3StorageProvider:
    """Singleton du stockage S3/MinIO (client boto3 réutilisé entre requêtes)."""
    return S3StorageProvider()


def get_storage() -> StorageProvider:
    """Dépendance FastAPI. Surchargée dans les tests par un stockage en mémoire."""
    return _default_storage()
