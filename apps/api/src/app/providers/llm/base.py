"""Interface commune des fournisseurs LLM + utilitaires de parsing JSON.

Chaque fournisseur (Groq, Gemini, HF...) implémente `generate_json` : il envoie
le prompt en demandant une sortie JSON et renvoie le dict parsé. La validation
métier (schéma Pydantic) est faite par la couche appelante (service extraction).
"""

import json
from typing import Any, Protocol, runtime_checkable


class LLMError(Exception):
    """Erreur d'un fournisseur LLM (indisponible, HTTP, réponse illisible)."""


@runtime_checkable
class LLMProvider(Protocol):
    """Fournisseur de complétion LLM renvoyant du JSON structuré."""

    @property
    def name(self) -> str: ...

    @property
    def available(self) -> bool:
        """Vrai si le fournisseur est configuré (clé API présente)."""
        ...

    async def generate_json(self, system: str, user: str) -> dict[str, Any]:
        """Envoie (system, user) et renvoie la réponse JSON parsée. Lève `LLMError`."""
        ...


def loads_json_object(text: str) -> dict[str, Any]:
    """Parse un objet JSON depuis la réponse d'un LLM.

    Tente `json.loads` direct ; à défaut, isole le 1er objet `{...}` (filet de
    sécurité si le modèle ajoute du texte autour). Lève `LLMError` si échec.
    """
    text = (text or "").strip()
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise LLMError("Réponse LLM sans objet JSON exploitable.") from None
        try:
            result = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMError("Réponse LLM : JSON invalide.") from exc

    if not isinstance(result, dict):
        raise LLMError("Réponse LLM : objet JSON attendu.")
    return result
