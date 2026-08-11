"""Fournisseur Google Drive — point d'entrée + injection FastAPI.

`get_drive_provider()` renvoie l'implémentation Google réelle si les
identifiants sont configurés (`GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON`), sinon lève
une erreur explicite. En test, la dépendance est surchargée par
`FakeDriveProvider` (aucun accès réseau).
"""

from functools import lru_cache

from app.core.config import settings
from app.providers.drive.base import DriveFile, DriveProvider, DriveProviderError
from app.providers.drive.fake import FakeDriveProvider
from app.providers.drive.google import GoogleDriveProvider

__all__ = [
    "DriveFile",
    "DriveProvider",
    "DriveProviderError",
    "FakeDriveProvider",
    "GoogleDriveProvider",
    "get_drive_provider",
]


@lru_cache
def _default_drive() -> DriveProvider:
    if not settings.google_drive_service_account_json:
        raise DriveProviderError(
            "Google Drive non configuré : renseigner "
            "GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON (JSON du compte de service, base64)."
        )
    return GoogleDriveProvider()


def get_drive_provider() -> DriveProvider:
    """Dépendance FastAPI : fournisseur Drive. Surchargée dans les tests."""
    return _default_drive()
