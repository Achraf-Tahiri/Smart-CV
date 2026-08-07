"""Fournisseur LLM simulé — pour les tests et le développement hors-ligne."""

from typing import Any

from app.providers.llm.base import LLMError


class FakeLLMProvider:
    name = "fake"

    def __init__(
        self,
        response: dict[str, Any] | None = None,
        *,
        fail: bool = False,
        available: bool = True,
    ) -> None:
        self._response = response or {}
        self._fail = fail
        self._available = available
        self.calls: list[tuple[str, str]] = []  # (system, user) reçus, pour assertions

    @property
    def available(self) -> bool:
        return self._available

    async def generate_json(self, system: str, user: str) -> dict[str, Any]:
        self.calls.append((system, user))
        if self._fail:
            raise LLMError("fake : échec simulé.")
        return dict(self._response)
