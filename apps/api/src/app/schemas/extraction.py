"""Schéma de sortie STRUCTURÉE de l'extraction LLM d'un CV.

Remplace le parsing fragile du POC (regex + ast.literal_eval) par une validation
Pydantic stricte. Le LLM doit produire un JSON conforme à ce schéma.
"""

from pydantic import BaseModel, Field, field_validator

from app.domain.taxonomies import SECTEURS_VALIDES


class ExtractedExperience(BaseModel):
    poste: str | None = None
    entreprise: str | None = None
    date_debut: str | None = None  # « YYYY-MM », « YYYY » ou brut (normalisé ensuite)
    date_fin: str | None = None  # idem, ou « PRESENT »
    description: str | None = None


class ExtractedActivity(BaseModel):
    titre: str | None = None
    organisation: str | None = None
    date_debut: str | None = None
    date_fin: str | None = None
    description: str | None = None


class ExtractedEducation(BaseModel):
    diplome: str | None = None
    ecole: str | None = None
    annee: str | None = None


class CVExtraction(BaseModel):
    """Résultat structuré de l'extraction d'un CV par le LLM."""

    prenom: str | None = None
    nom: str | None = None
    email: str | None = None
    telephone: str | None = None
    ville: str | None = None
    poste_actuel: str | None = None
    secteur: str = "Autre"
    specialite: str | None = None
    experiences: list[ExtractedExperience] = Field(default_factory=list)
    activites_extra: list[ExtractedActivity] = Field(default_factory=list)
    formations: list[ExtractedEducation] = Field(default_factory=list)
    hard_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    langues: list[str] = Field(default_factory=list)

    @field_validator("secteur", mode="before")
    @classmethod
    def _coerce_secteur(cls, value: object) -> str:
        """Force le secteur dans la taxonomie ; toute valeur inconnue -> « Autre »."""
        if isinstance(value, str) and value in SECTEURS_VALIDES:
            return value
        return "Autre"
