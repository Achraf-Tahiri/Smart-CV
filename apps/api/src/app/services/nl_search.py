"""Recherche en langage naturel : NL query → filtres structurés → recherche hybride.

Le LLM (via LLMProvider) extrait les filtres depuis une requête libre, puis
hybrid_search() applique la recherche sur la base.

Fonctionne SANS clé LLM en test grâce à FakeLLMProvider.
En production, GROQ_API_KEY est requis pour l'extraction NL réelle.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.taxonomies import SECTEURS_VALIDES, SENIORITE_THRESHOLDS
from app.models.candidate import Candidate
from app.providers.embeddings import EmbeddingProvider
from app.providers.llm import LLMError, LLMProvider
from app.services.search import hybrid_search

# ---------------------------------------------------------------------------
# Constantes portées du POC (analyzer.py l.887 et l.898)
# ---------------------------------------------------------------------------

# Villes qui sont aussi des prénoms courants → si le LLM place l'un d'eux dans
# "ville", on le déplace dans "keywords" (portage de analyzer.py l.887).
AMBIGUOUS_NAMES: frozenset[str] = frozenset(
    {
        "doha",
        "sofia",
        "alexandria",
        "victoria",
        "charlotte",
        "virginia",
        "austin",
        "orlando",
    }
)

# Termes génériques interdits dans les mots-clés (portage de analyzer.py l.898).
STOP_WORDS: frozenset[str] = frozenset(
    {
        "candidat",
        "candidats",
        "profil",
        "profils",
        "cv",
        "cvs",
        "personne",
        "gens",
        "je",
        "veux",
        "recherche",
        "cherche",
        "trouve",
        "moi",
        "besoin",
        "débutant",
        "debutant",
        "junior",
        "juniors",
        "confirmé",
        "confirme",
        "intermédiaire",
        "senior",
        "seniors",
        "expert",
        "experts",
        "expérimenté",
        "experimente",
    }
)

# Labels de séniorité valides — source unique : SENIORITE_THRESHOLDS (domain/taxonomies).
_VALID_SENIORITE: frozenset[str] = frozenset(label for _, _, label in SENIORITE_THRESHOLDS)

# Mapping termes informels → label canonique du barème unifié.
# Porte le prompt POC l.849-852 sans réintroduire ses incohérences de seuils.
_SENIORITE_INFORMAL_MAP: dict[str, str] = {
    "débutant": "Stage / Junior",
    "debutant": "Stage / Junior",
    "stage": "Stage / Junior",
    "junior": "Junior",
    "juniors": "Junior",
    "confirmé": "Intermédiaire",
    "confirme": "Intermédiaire",
    "intermédiaire": "Intermédiaire",
    "intermediaire": "Intermédiaire",
    "expérimenté": "Senior",
    "experimente": "Senior",
    "senior": "Senior",
    "seniors": "Senior",
    "expert": "Lead / Expert",
    "experts": "Lead / Expert",
    "lead": "Lead / Expert",
}


# ---------------------------------------------------------------------------
# Schéma Pydantic de sortie du LLM
# ---------------------------------------------------------------------------


class NLSearchFilters(BaseModel):
    """Filtres structurés extraits d'une requête en langage naturel par le LLM."""

    keywords: list[str] = Field(default_factory=list)
    ville: str | None = None
    secteur: str | None = None
    seniorite: str | None = None
    min_experience: float | None = None
    max_experience: float | None = None

    @field_validator("secteur", mode="before")
    @classmethod
    def _coerce_secteur(cls, v: Any) -> str | None:
        if isinstance(v, str) and v in SECTEURS_VALIDES:
            return v
        return None

    @field_validator("seniorite", mode="before")
    @classmethod
    def _coerce_seniorite(cls, v: Any) -> str | None:
        if not isinstance(v, str):
            return None
        if v in _VALID_SENIORITE:
            return v
        return _SENIORITE_INFORMAL_MAP.get(v.lower())

    @field_validator("min_experience", "max_experience", mode="before")
    @classmethod
    def _coerce_experience(cls, v: Any) -> float | None:
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None


# ---------------------------------------------------------------------------
# Prompt LLM
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "Tu es un expert RH. "
    "Tu traduis des requêtes recruteur en filtres JSON structurés. "
    "Tu réponds UNIQUEMENT avec un objet JSON valide, sans texte autour."
)


def _build_user_prompt(query: str) -> str:
    secteurs = ", ".join(SECTEURS_VALIDES)
    seniorites = ", ".join(label for _, _, label in SENIORITE_THRESHOLDS)
    return f"""Traduis cette requête recruteur en filtres JSON.

SECTEURS VALIDES (choisis parmi ces valeurs EXACTES ou null) :
{secteurs}

NIVEAUX DE SÉNIORITÉ VALIDES (choisis parmi ces valeurs EXACTES ou null) :
{seniorites}

RÈGLES :
1. keywords : compétences techniques au singulier (ex: "Python", "React").
   INTERDIT : termes de niveau (junior, senior...), mots génériques (candidat, profil, cv...).
   Si un nom propre est ambigu avec une ville (ex: "Doha"), mets-le dans keywords plutôt que ville.
2. ville : localisation EXPLICITE uniquement (ex: "à Casablanca", "basé à Rabat").
3. secteur : une valeur EXACTE de la liste ci-dessus, ou null.
4. seniorite : une valeur EXACTE de la liste ci-dessus, ou null.
5. min_experience / max_experience : en années (float), ou null.

FORMAT JSON STRICT :
{{
  "keywords": ["mot1", "mot2"],
  "ville": "string ou null",
  "secteur": "string ou null",
  "seniorite": "string ou null",
  "min_experience": float ou null,
  "max_experience": float ou null
}}

REQUÊTE : "{query}"

RÉPONSE JSON UNIQUEMENT :"""


# ---------------------------------------------------------------------------
# Fonctions publiques
# ---------------------------------------------------------------------------


def apply_postprocessing(filters: NLSearchFilters) -> NLSearchFilters:
    """Post-traitements code-level portés du POC (analyzer.py l.885-913).

    1. AMBIGUOUS_NAMES : ville ambiguë (aussi prénom courant) → déplacée dans keywords.
    2. STOP_WORDS : termes interdits retirés des keywords.
    """
    data = filters.model_dump()

    ville = (data.get("ville") or "").strip()
    if ville and ville.lower() in AMBIGUOUS_NAMES:
        data["keywords"] = list(data.get("keywords") or []) + [ville]
        data["ville"] = None

    data["keywords"] = [k for k in (data.get("keywords") or []) if k.lower() not in STOP_WORDS]

    return NLSearchFilters.model_validate(data)


async def parse_nl_query(llm: LLMProvider, query: str) -> NLSearchFilters:
    """Traduit une requête NL en NLSearchFilters via le LLM + post-traitements.

    En cas d'erreur LLM (clé absente, timeout, JSON invalide), retourne des
    filtres vides plutôt que de lever une exception.
    """
    try:
        raw = await llm.generate_json(_SYSTEM_PROMPT, _build_user_prompt(query))
    except LLMError:
        raw = {}

    filters = NLSearchFilters.model_validate(raw)
    return apply_postprocessing(filters)


async def nl_search(
    session: AsyncSession,
    embeddings: EmbeddingProvider,
    llm: LLMProvider,
    *,
    query: str,
    limit: int = 20,
    offset: int = 0,
) -> tuple[int, list[Candidate]]:
    """Recherche en langage naturel : parse la requête puis délègue à hybrid_search.

    Les mots-clés extraits alimentent la recherche hybride (plein-texte + vecteurs) ;
    les autres filtres (ville, secteur, séniorité, expérience) sont passés directement.
    """
    filters = await parse_nl_query(llm, query)
    q = " ".join(filters.keywords) if filters.keywords else None
    return await hybrid_search(
        session,
        embeddings,
        q=q,
        secteur=filters.secteur,
        ville=filters.ville,
        seniorite=filters.seniorite,
        min_experience=filters.min_experience,
        max_experience=filters.max_experience,
        limit=limit,
        offset=offset,
    )
