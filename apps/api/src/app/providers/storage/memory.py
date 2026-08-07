"""Stockage en mémoire — uniquement pour les tests (aucune dépendance réseau)."""


class InMemoryStorageProvider:
    """Implémentation de `StorageProvider` basée sur un dictionnaire."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    async def put(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        self._objects[key] = data

    async def get(self, key: str) -> bytes:
        return self._objects[key]

    async def delete(self, key: str) -> None:
        self._objects.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self._objects

    async def presigned_url(self, key: str, *, expires_in: int = 3600) -> str:
        return f"memory://{key}?expires_in={expires_in}"
