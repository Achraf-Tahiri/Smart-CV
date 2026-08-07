"""Upload et téléchargement de documents (fichiers CV).

- upload : réservé au recruteur (+ admin), dédup par hash, trace d'audit ;
- download-url : tout utilisateur authentifié, renvoie une URL signée (jamais
  de fichier servi en statique).
"""

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.api.deps import CurrentUser, EmbeddingsDep, LLMDep, SessionDep, StorageDep, require_role
from app.core.config import settings
from app.models.candidate import Document
from app.models.enums import Source, UserRole
from app.models.user import User
from app.schemas.candidate import CandidateRead
from app.schemas.document import DocumentUploadResult, DownloadUrl
from app.services import audit, ingestion
from app.services import documents as documents_service

router = APIRouter(tags=["documents"])

WriterUser = Annotated[User, Depends(require_role(UserRole.recruteur))]

# Formats acceptés (CV) : PDF, Word, images (pour l'OCR en Phase 2).
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"}


@router.post(
    "/upload",
    response_model=DocumentUploadResult,
    status_code=status.HTTP_201_CREATED,
    summary="Importer un document (CV)",
)
async def upload_document(
    request: Request,
    session: SessionDep,
    storage: StorageDep,
    current_user: WriterUser,
    file: Annotated[UploadFile, File(description="Fichier CV (PDF, Word ou image).")],
):
    filename = file.filename or "document"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        accepted = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Format non supporté ({ext}). Acceptés : {accepted}.",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fichier vide.")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Fichier trop volumineux (max {settings.max_upload_mb} Mo).",
        )

    document, created = await documents_service.import_document(
        session,
        storage,
        filename=filename,
        content_type=file.content_type,
        data=data,
        source=Source.local,
        created_by_id=current_user.id,
    )
    if created:
        await audit.record(
            session,
            action="document.upload",
            user_id=current_user.id,
            entity_type="document",
            entity_id=document.id,
            details={"filename": filename, "candidate_id": str(document.candidate_id)},
            ip_address=request.client.host if request.client else None,
        )
    await session.commit()

    return DocumentUploadResult(
        candidate_id=document.candidate_id,
        document_id=document.id,
        filename=document.filename,
        file_hash=document.file_hash or "",
        deduplicated=not created,
    )


@router.post(
    "/{document_id}/process",
    response_model=CandidateRead,
    summary="Traiter un document (extraction IA -> candidat structuré)",
)
async def process_document(
    request: Request,
    document_id: uuid.UUID,
    session: SessionDep,
    storage: StorageDep,
    llm: LLMDep,
    embeddings: EmbeddingsDep,
    current_user: WriterUser,
):
    """Lance le pipeline d'ingestion (synchrone en V1 ; passera en file de jobs
    en Phase 3). Le candidat renvoyé porte le statut du traitement (`success`
    ou `manual_review` en cas d'échec d'extraction).
    """
    document = await session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable.")

    candidate = await ingestion.process_document(
        session, document=document, llm=llm, embeddings=embeddings, storage=storage
    )
    await audit.record(
        session,
        action="document.process",
        user_id=current_user.id,
        entity_type="candidate",
        entity_id=candidate.id,
        details={"status": candidate.status.value},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(candidate)
    return candidate


@router.get(
    "/{document_id}/download-url",
    response_model=DownloadUrl,
    summary="URL signée de téléchargement d'un document",
)
async def get_download_url(
    document_id: uuid.UUID,
    session: SessionDep,
    storage: StorageDep,
    _user: CurrentUser,
):
    document = await session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable.")
    expires_in = 3600
    url = await storage.presigned_url(document.storage_key, expires_in=expires_in)
    return DownloadUrl(url=url, expires_in=expires_in)
