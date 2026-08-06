"""Base déclarative SQLAlchemy 2.0, commune à tous les modèles ORM."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Classe de base dont héritent tous les modèles (remplis en Phase 1)."""
