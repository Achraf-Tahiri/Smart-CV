"""Schémas Pydantic pour les candidats.

Note : l'email du candidat est typé `str` (et non `EmailStr`) volontairement.
C'est une donnée extraite de CV, souvent bruitée ; on ne veut pas rejeter un
enregistrement pour un email mal formé (l'utilisateur système, lui, a un EmailStr).
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import CandidateStatus, SkillType, Source


class CandidateBase(BaseModel):
    """Champs éditables communs à la création et à la mise à jour."""

    prenom: str | None = None
    nom: str | None = None
    email: str | None = None
    telephone: str | None = None
    ville: str | None = None
    poste_actuel: str | None = None
    secteur: str | None = None
    specialite: str | None = None
    annees_experience: float = 0.0
    experience_texte: str | None = None
    seniorite: str | None = None


class CandidateCreate(CandidateBase):
    """Création manuelle d'un candidat (source locale, statut prêt par défaut)."""

    source: Source = Source.local
    status: CandidateStatus = CandidateStatus.success


class CandidateUpdate(BaseModel):
    """Mise à jour partielle (PATCH) : tous les champs sont optionnels."""

    prenom: str | None = None
    nom: str | None = None
    email: str | None = None
    telephone: str | None = None
    ville: str | None = None
    poste_actuel: str | None = None
    secteur: str | None = None
    specialite: str | None = None
    annees_experience: float | None = None
    experience_texte: str | None = None
    seniorite: str | None = None
    status: CandidateStatus | None = None


class CandidateRead(BaseModel):
    """Représentation d'un candidat renvoyée par l'API (vue liste et détail)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    prenom: str | None
    nom: str | None
    email: str | None
    telephone: str | None
    ville: str | None
    poste_actuel: str | None
    secteur: str | None
    specialite: str | None
    annees_experience: float
    experience_texte: str | None
    seniorite: str | None
    status: CandidateStatus
    source: Source
    created_at: datetime
    updated_at: datetime


# --- Schémas imbriqués (fiche détaillée) ---


class ExperienceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    poste: str | None
    entreprise: str | None
    date_debut: date | None
    date_fin: date | None
    is_current: bool
    description: str | None


class EducationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    diplome: str | None
    ecole: str | None
    annee: int | None
    description: str | None


class ActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    titre: str | None
    organisation: str | None
    date_debut: date | None
    date_fin: date | None
    is_current: bool
    description: str | None


class SkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: SkillType


class LanguageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    level: str | None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    content_type: str | None
    source: Source
    created_at: datetime


class CandidateDetail(CandidateRead):
    """Fiche complète : champs du candidat + son parcours et ses documents."""

    experiences: list[ExperienceRead] = []
    educations: list[EducationRead] = []
    activites_extra: list[ActivityRead] = []
    skills: list[SkillRead] = []
    langues: list[LanguageRead] = []
    documents: list[DocumentRead] = []


class CandidateStats(BaseModel):
    """Agrégats pour le tableau de bord."""

    total: int
    by_status: dict[str, int]
    by_secteur: dict[str, int]
    by_seniorite: dict[str, int]
