"""Dépendances FastAPI réutilisables : session DB, utilisateur courant, RBAC."""

import uuid
from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.enums import UserRole
from app.models.user import User
from app.providers.embeddings import EmbeddingProvider, get_embeddings
from app.providers.llm import LLMProvider, get_llm
from app.providers.storage import StorageProvider, get_storage
from app.services import users as users_service

# Session DB injectée par requête.
SessionDep = Annotated[AsyncSession, Depends(get_session)]

# Stockage d'objets (S3/MinIO) injecté par requête.
StorageDep = Annotated[StorageProvider, Depends(get_storage)]

# Fournisseur LLM (cascade) injecté par requête.
LLMDep = Annotated[LLMProvider, Depends(get_llm)]

# Fournisseur d'embeddings injecté par requête.
EmbeddingsDep = Annotated[EmbeddingProvider, Depends(get_embeddings)]

# Schéma OAuth2 « password » : Swagger affiche un bouton « Authorize ».
# tokenUrl doit pointer vers l'endpoint de login (chemin complet, sans slash initial).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

_credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Identifiants invalides ou jeton expiré.",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: SessionDep,
) -> User:
    """Décode le JWT, charge l'utilisateur et vérifie qu'il est actif."""
    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        if subject is None:
            raise _credentials_error
        user_id = uuid.UUID(str(subject))
    except (jwt.PyJWTError, ValueError) as exc:
        raise _credentials_error from exc

    user = await users_service.get_by_id(session, user_id)
    if user is None or not user.is_active:
        raise _credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*allowed_roles: UserRole) -> Callable[[User], User]:
    """Fabrique une dépendance qui exige un des rôles donnés.

    Le rôle `admin` est toujours autorisé (super-utilisateur).

    Exemple :
        @router.post(..., dependencies=[Depends(require_role(UserRole.recruteur))])
    """
    allowed = {UserRole.admin, *allowed_roles}

    def checker(current_user: CurrentUser) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'avez pas les droits nécessaires pour cette action.",
            )
        return current_user

    return checker
