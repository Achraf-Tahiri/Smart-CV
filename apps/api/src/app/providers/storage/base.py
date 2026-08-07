"""Interface du fournisseur de stockage d'objets (fichiers).

Toute implémentation (S3/MinIO en local, S3/GCS en cloud, faux en mémoire pour
les tests) respecte ce protocole → on change de stockage sans toucher au métier.
"""

from typing import Protocol


class StorageProvider(Protocol):
    """Stockage d'objets binaires adressés par une clé (chemin logique)."""

    async def put(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        """Écrit (ou remplace) l'objet à la clé donnée."""
        ...

    async def get(self, key: str) -> bytes:
        """Lit le contenu de l'objet. Lève si absent."""
        ...

    async def delete(self, key: str) -> None:
        """Supprime l'objet (idempotent)."""
        ...

    async def exists(self, key: str) -> bool:
        """Indique si un objet existe à cette clé."""
        ...

    async def presigned_url(self, key: str, *, expires_in: int = 3600) -> str:
        """Retourne une URL signée temporaire pour télécharger l'objet."""
        ...
