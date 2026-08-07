"""Fournisseur d'embeddings — point d'entrée + injection FastAPI."""

from functools import lru_cache

from app.core.config import settings
from app.providers.embeddings.base import EmbeddingProvider
from app.providers.embeddings.deterministic import DeterministicEmbeddingProvider

__all__ = ["EmbeddingProvider", "get_embeddings"]


@lru_cache
def _default_embeddings() -> EmbeddingProvider:
    if settings.embeddings_backend == "sentence-transformers":
        # Import paresseux : ne charge torch que si ce backend est choisi.
        from app.providers.embeddings.sentence_transformer import (
            SentenceTransformerEmbeddingProvider,
        )

        return SentenceTransformerEmbeddingProvider(
            settings.embeddings_model, settings.embeddings_dim
        )
    return DeterministicEmbeddingProvider(settings.embeddings_dim)


def get_embeddings() -> EmbeddingProvider:
    """Dépendance FastAPI : le fournisseur d'embeddings (déterministe par défaut)."""
    return _default_embeddings()
