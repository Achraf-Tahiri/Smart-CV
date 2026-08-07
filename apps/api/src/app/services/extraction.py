"""Extraction structurée d'un CV via LLM.

Porte le gros prompt FR du POC (règles de séparation expérience/formation/
associatif, dates, secteur imposé), mais :
- **sortie structurée validée par Pydantic** (fini regex + ast.literal_eval) ;
- **pas de troncature à 4000 caractères** (limite large et configurable) ;
- **un réessai** en cas de JSON non conforme au schéma.
"""

from pydantic import ValidationError

from app.core.config import settings
from app.domain.taxonomies import SECTEURS_VALIDES
from app.providers.llm import LLMError, LLMProvider
from app.schemas.extraction import CVExtraction

_SYSTEM = (
    "Tu es un expert RH spécialisé dans l'analyse de CV. "
    "Tu réponds UNIQUEMENT avec un objet JSON valide, sans aucun texte autour."
)


def build_prompt(text: str) -> str:
    """Construit le prompt utilisateur (schéma + règles + CV)."""
    secteurs = ", ".join(SECTEURS_VALIDES)
    return f"""Analyse ce CV et extrais les informations au format JSON strict suivant :

{{
  "prenom": "string|null (EXTRACTION EXACTE, ne corrige pas l'orthographe)",
  "nom": "string|null (EXTRACTION EXACTE)",
  "email": "string|null",
  "telephone": "string|null",
  "ville": "string|null (ville principale UNIQUEMENT, jamais le quartier)",
  "poste_actuel": "string|null (titre principal, sinon dernier poste)",
  "secteur": "string OBLIGATOIRE parmi : {secteurs}",
  "specialite": "string|null (ex: 'Data Science', 'DevOps')",
  "experiences": [
    {{"poste": "string", "entreprise": "string", "date_debut": "YYYY-MM",
      "date_fin": "YYYY-MM ou 'PRESENT'", "description": "string|null"}}
  ],
  "activites_extra": [
    {{"titre": "string", "organisation": "string", "date_debut": "YYYY-MM",
      "date_fin": "YYYY-MM", "description": "string"}}
  ],
  "formations": [{{"diplome": "string", "ecole": "string", "annee": "YYYY|null"}}],
  "hard_skills": ["string"],
  "soft_skills": ["string"],
  "langues": ["Français (natif)", "Anglais (courant)"]
}}

RÈGLES :
1. "secteur" : choisis OBLIGATOIREMENT une valeur EXACTE de la liste ci-dessus.
2. Dates en "YYYY-MM" (ou "YYYY"). "Depuis 2023" -> date_debut="2023", date_fin="PRESENT".
   ATTENTION : "2023-2024" signifie fin=2024, PAS "PRESENT". Ne mets JAMAIS de mois par défaut.
3. SÉPARATION STRICTE : Bénévolat / Associatif / Club (Association Démo, JCI, Rotaract...) vont dans
   "activites_extra", PAS dans "experiences".
4. SÉPARATION FORMATION/EXPÉRIENCE : tout diplôme (Bac, Licence, Master, Ingénieur, Doctorat)
   et toute certification vont dans "formations". Seuls stages, emplois et freelance vont dans
   "experiences".
5. NE FUSIONNE PAS deux blocs visuellement distincts : crée deux entrées séparées.
6. Valeurs manquantes -> null (le JSON null), JAMAIS la chaîne "null"/"None"/"Vide".
7. "ville" : si "Sidi Bernoussi, Casablanca" -> "Casablanca".

Inclus TOUTE expérience pertinente même junior (stages >= 3 mois, PFE significatifs, freelance).

CV À ANALYSER :
{text}"""


async def extract_cv(llm: LLMProvider, text: str) -> CVExtraction:
    """Extrait les données structurées d'un CV. Lève `LLMError` en cas d'échec."""
    text = (text or "").strip()
    if not text:
        raise LLMError("Texte de CV vide : rien à extraire.")
    text = text[: settings.llm_max_input_chars]

    prompt = build_prompt(text)
    raw = await llm.generate_json(_SYSTEM, prompt)
    try:
        return CVExtraction.model_validate(raw)
    except ValidationError:
        # 2e tentative avec un rappel de conformité stricte.
        strict = (
            prompt + "\n\nRAPPEL : réponds STRICTEMENT avec l'objet JSON du schéma, rien d'autre."
        )
        raw = await llm.generate_json(_SYSTEM, strict)
        try:
            return CVExtraction.model_validate(raw)
        except ValidationError as exc:
            raise LLMError(
                f"Extraction non conforme au schéma : {exc.error_count()} erreur(s)."
            ) from exc
