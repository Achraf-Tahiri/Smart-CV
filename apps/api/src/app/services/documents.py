"""Service : import de documents (fichiers CV) avec déduplication.

Convention : ne committe pas (l'appelant gère la transaction).

Note : l'objet binaire est écrit dans le stockage AVANT le commit DB. Si le
commit échoue ensuite, un objet orphelin peut subsister côté stockage (cas rare,
nettoyable par une réconciliation ultérieure — Phase 5).
"""

import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate, Document
from app.models.enums import CandidateStatus, Source
from app.providers.storage import StorageProvider


def storage_key_for(document_id: uuid.UUID) -> str:
    """Clé de stockage d'un document (adressage par identifiant, pas par nom)."""
    return f"documents/{document_id}"


async def import_document(
    session: AsyncSession,
    storage: StorageProvider,
    *,
    filename: str,
    content_type: str | None,
    data: bytes,
    source: Source = Source.local,
    created_by_id: uuid.UUID | None = None,
) -> tuple[Document, bool]:
    """Importe un document.

    Déduplique par SHA-256 du contenu : si le fichier existe déjà, retourne le
    document existant sans rien recréer. Sinon crée un `Candidate` (statut
    `pending`, à traiter par le pipeline IA) + un `Document`, et écrit le binaire.

    Retour : (document, created) — `created=False` si c'était un doublon.
    """
    file_hash = hashlib.sha256(data).hexdigest()

    existing = (
        await session.execute(select(Document).where(Document.file_hash == file_hash))
    ).scalar_one_or_none()
    if existing is not None:
        return existing, False

    candidate = Candidate(
        id=uuid.uuid4(),
        source=source,
        status=CandidateStatus.pending,
        created_by_id=created_by_id,
    )
    document_id = uuid.uuid4()
    document = Document(
        id=document_id,
        candidate_id=candidate.id,
        storage_key=storage_key_for(document_id),
        filename=filename,
        content_type=content_type,
        size_bytes=len(data),
        file_hash=file_hash,
        source=source,
    )
    session.add(candidate)
    session.add(document)
    await session.flush()

    await storage.put(document.storage_key, data, content_type=content_type)
    return document, True
