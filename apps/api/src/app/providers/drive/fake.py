"""Fournisseur Drive en mémoire — usage tests uniquement (aucun réseau)."""

from app.providers.drive.base import DriveFile, DriveProviderError


class FakeDriveProvider:
    """Implémentation de `DriveProvider` basée sur un dictionnaire en mémoire.

    Permet de tester la synchro (dédup, idempotence, mise en file de l'ingestion)
    sans dépendance réseau. Les tests injectent les fichiers via `add()`.
    """

    def __init__(self) -> None:
        self._files: dict[str, tuple[DriveFile, bytes, str | None]] = {}
        self._folders: dict[str, list[str]] = {}
        self.download_calls: list[str] = []  # observabilité pour les tests

    def add(
        self,
        *,
        folder_id: str,
        file: DriveFile,
        data: bytes,
        content_type: str | None = None,
    ) -> None:
        """Ajoute un fichier au dossier virtuel (utilisé par les tests)."""
        self._files[file.id] = (file, data, content_type)
        self._folders.setdefault(folder_id, []).append(file.id)

    def remove(self, folder_id: str, file_id: str) -> None:
        """Retire un fichier (simule une suppression côté Drive)."""
        self._files.pop(file_id, None)
        if folder_id in self._folders:
            self._folders[folder_id] = [i for i in self._folders[folder_id] if i != file_id]

    async def list_files(self, folder_id: str) -> list[DriveFile]:
        return [self._files[i][0] for i in self._folders.get(folder_id, []) if i in self._files]

    async def download_file(self, file_id: str) -> tuple[bytes, str | None]:
        self.download_calls.append(file_id)
        if file_id not in self._files:
            raise DriveProviderError(f"Fichier absent : {file_id}")
        _meta, data, ctype = self._files[file_id]
        return data, ctype

    def get_view_url(self, file_id: str) -> str:
        return f"https://drive.google.com/file/d/{file_id}/view"
