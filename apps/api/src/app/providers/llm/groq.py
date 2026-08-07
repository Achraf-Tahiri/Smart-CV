"""Fournisseur LLM : Groq (API compatible OpenAI, JSON mode natif)."""

from typing import Any

import httpx

from app.core.config import settings
from app.providers.llm.base import LLMError, loads_json_object
from app.providers.llm.http import post_json


class GroqProvider:
    name = "groq"
    _URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, *, client: httpx.AsyncClient | None = None) -> None:
        self._client = client  # injectable pour les tests

    @property
    def available(self) -> bool:
        return bool(settings.groq_api_key)

    async def generate_json(self, system: str, user: str) -> dict[str, Any]:
        if not self.available:
            raise LLMError("Groq : clé API absente (GROQ_API_KEY).")
        data = await post_json(
            self._URL,
            json_body={
                "model": settings.groq_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            client=self._client,
        )
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Groq : format de réponse inattendu.") from exc
        return loads_json_object(content)
