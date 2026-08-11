"""Fournisseur Google Drive (compte de service).

⚠️ Squelette : les identifiants (JSON du compte de service, base64) sont lus
uniquement depuis la variable d'environnement `GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON`.
**Aucun secret n'est jamais écrit sur disque** (le POC le faisait — bug corrigé).

Les dépendances `google-api-python-client` / `google-auth` sont importées
paresseusement dans `_build_service()` : tant qu'elles ne sont pas installées ou
que la clé n'est pas fournie, l'implémentation refuse simplement de démarrer
(elle ne casse pas l'import global du package).

Pour activer l'implémentation réelle :
    1. Ajouter `google-api-python-client` et `google-auth` aux dépendances API.
    2. Renseigner `GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON` (JSON du compte, base64).
"""

import base64
import binascii
import json
from typing import Any

from anyio import to_thread

from app.core.config import settings
from app.providers.drive.base import DriveFile, DriveProviderError


class GoogleDriveProvider:
    """Fournisseur Google Drive via un compte de service (lecture seule)."""

    _SCOPES = ("https://www.googleapis.com/auth/drive.readonly",)

    def __init__(self) -> None:
        if not settings.google_drive_service_account_json:
            raise DriveProviderError(
                "GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON manquant : fournisseur Google inactif."
            )
        self._service: Any | None = None

    def _load_credentials_info(self) -> dict[str, Any]:
        """Décode la clé du compte de service (JSON base64) depuis l'environnement."""
        raw = settings.google_drive_service_account_json
        try:
            decoded = base64.b64decode(raw, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise DriveProviderError(
                "GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON : base64 invalide."
            ) from exc
        try:
            return json.loads(decoded)
        except json.JSONDecodeError as exc:
            raise DriveProviderError(
                "GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON : JSON invalide après décodage."
            ) from exc

    def _build_service(self) -> Any:
        """Construit le client Drive à la demande (imports paresseux)."""
        if self._service is not None:
            return self._service
        try:  # pragma: no cover — dépend d'un extra optionnel
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError as exc:  # pragma: no cover
            raise DriveProviderError(
                "google-api-python-client / google-auth non installés."
            ) from exc

        info = self._load_credentials_info()
        creds = service_account.Credentials.from_service_account_info(info, scopes=self._SCOPES)
        self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return self._service

    async def list_files(self, folder_id: str) -> list[DriveFile]:
        """Liste paginée des fichiers du dossier (hors sous-dossiers)."""
        service = self._build_service()
        return await to_thread.run_sync(self._list_files_sync, service, folder_id)

    @staticmethod
    def _list_files_sync(service: Any, folder_id: str) -> list[DriveFile]:  # pragma: no cover
        query = (
            f"'{folder_id}' in parents and trashed = false "
            "and mimeType != 'application/vnd.google-apps.folder'"
        )
        fields = "nextPageToken, files(id, name, mimeType, size, modifiedTime, md5Checksum)"
        page_token: str | None = None
        results: list[DriveFile] = []
        while True:
            response = (
                service.files()
                .list(
                    q=query,
                    fields=fields,
                    pageSize=1000,
                    pageToken=page_token,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )
            for item in response.get("files", []):
                results.append(
                    DriveFile(
                        id=item["id"],
                        name=item.get("name", ""),
                        mime_type=item.get("mimeType", ""),
                        size=int(item["size"]) if item.get("size") else None,
                        modified_time=None,  # ISO string à parser si besoin plus tard
                        md5_checksum=item.get("md5Checksum"),
                    )
                )
            page_token = response.get("nextPageToken")
            if not page_token:
                return results

    async def download_file(self, file_id: str) -> tuple[bytes, str | None]:
        service = self._build_service()
        return await to_thread.run_sync(self._download_file_sync, service, file_id)

    @staticmethod
    def _download_file_sync(  # pragma: no cover
        service: Any, file_id: str
    ) -> tuple[bytes, str | None]:
        from io import BytesIO

        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaIoBaseDownload

        try:
            meta = (
                service.files()
                .get(fileId=file_id, fields="mimeType", supportsAllDrives=True)
                .execute()
            )
            request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
            buffer = BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _status, done = downloader.next_chunk()
            return buffer.getvalue(), meta.get("mimeType")
        except HttpError as exc:
            raise DriveProviderError(str(exc)) from exc

    def get_view_url(self, file_id: str) -> str:
        return f"https://drive.google.com/file/d/{file_id}/view"
