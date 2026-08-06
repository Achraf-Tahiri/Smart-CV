"""Modèles ORM — import centralisé.

Importer ce module suffit à enregistrer toutes les tables dans
``Base.metadata`` (utile pour Alembic et la création du schéma).
"""

from app.models.audit import AuditLog
from app.models.candidate import Candidate, Document
from app.models.embedding import CandidateEmbedding
from app.models.experience import Education, Experience, ExtraActivity
from app.models.job import ImportJob, SyncState
from app.models.skill import CandidateLanguage, CandidateSkill, Skill
from app.models.user import User

__all__ = [
    "AuditLog",
    "Candidate",
    "CandidateEmbedding",
    "CandidateLanguage",
    "CandidateSkill",
    "Document",
    "Education",
    "Experience",
    "ExtraActivity",
    "ImportJob",
    "Skill",
    "SyncState",
    "User",
]
