"""Schémas Pydantic pour les utilisateurs."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class UserCreate(BaseModel):
    """Données de création d'un utilisateur (seed admin, gestion des comptes)."""

    email: EmailStr
    password: str = Field(min_length=8, description="Mot de passe en clair (min. 8 caractères).")
    full_name: str | None = None
    role: UserRole = UserRole.lecteur


class UserRead(BaseModel):
    """Représentation publique d'un utilisateur (jamais le hash du mot de passe)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: UserRole
    is_active: bool
    created_at: datetime
