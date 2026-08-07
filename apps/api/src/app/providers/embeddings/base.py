"""Interface des fournisseurs d'embeddings (vecteurs pour la recherche sémantique).

Une implémentation transforme du texte en vecteur de dimension fixe. La distance
cosinus entre vecteurs mesure la similarité (recherche vectorielle via pgvector).
"""

from typing import Protocol


class EmbeddingProvider(Protocol):
    @property
    def dimension(self) -> int:
        """Dimension des vecteurs produits (doit correspondre à la colonne pgvector)."""
        ...

    async def embed_query(self, text: str) -> list[float]:
        """Vecteur d'une requête de recherche."""
        ...

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Vecteurs d'un lot de documents."""
        ...
