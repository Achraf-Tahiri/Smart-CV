"""Cascade de fournisseurs LLM : essaie chacun dans l'ordre jusqu'au premier succès."""

from typing import Any

from app.providers.llm.base import LLMError, LLMProvider


class CascadeLLMProvider:
    name = "cascade"

    def __init__(self, providers: list[LLMProvider]) -> None:
        self._providers = providers

    @property
    def available(self) -> bool:
        return any(p.available for p in self._providers)

    async def generate_json(self, system: str, user: str) -> dict[str, Any]:
        errors: list[str] = []
        for provider in self._providers:
            if not provider.available:
                continue
            try:
                return await provider.generate_json(system, user)
            except LLMError as exc:
                errors.append(f"{provider.name}: {exc}")

        if not errors:
            raise LLMError("Aucun fournisseur LLM configuré (renseigne une clé API dans .env).")
        raise LLMError("Tous les fournisseurs LLM ont échoué. " + " | ".join(errors))
