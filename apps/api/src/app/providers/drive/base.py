"""Interface d'accès à un espace Google Drive (fournisseur remplaçable).

Toute implémentation (Google Drive réel via service account, faux en mémoire
pour les tests) respecte ce protocole → on change de fournisseur sans toucher
au métier (service de synchro, tâche Arq, endpoints).

Aucune implémentation ne DOIT écrire de secrets sur disque : les identifiants
du compte de service sont lus depuis l'environnement (variable
`GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON`, JSON encodé en base64).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class DriveFile:
    """Métadonnées d'un fichier Google Drive (structure indépendante du SDK)."""

    id: str  # identifiant Drive stable (mappé sur Document.drive_file_id)
    name: str  # nom du fichier (extension incluse)
    mime_type: str
    size: int | None = None
    modified_time: datetime | None = None
    md5_checksum: str | None = None  # optionnel : dédup rapide sans télécharger


class DriveProviderError(Exception):
    """Erreur générique d'un fournisseur Drive (auth, réseau, quota…)."""


class DriveProvider(Protocol):
    """Fournisseur d'accès à un dossier Google Drive (lecture seule)."""

    async def list_files(self, folder_id: str) -> list[DriveFile]:
        """Liste récursive des fichiers du dossier (sans dossiers). Peut lever."""
        ...

    async def download_file(self, file_id: str) -> tuple[bytes, str | None]:
        """Télécharge le contenu binaire d'un fichier. Retour : (data, content_type).

        Doit lever `DriveProviderError` en cas d'échec définitif.
        """
        ...

    def get_view_url(self, file_id: str) -> str:
        """URL de visualisation Drive (ouverte dans un onglet, pas un download)."""
        ...
