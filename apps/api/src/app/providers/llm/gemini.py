"""Fournisseur LLM : Google Gemini (generateContent, sortie JSON)."""

from typing import Any

import httpx

from app.core.config import settings
from app.providers.llm.base import LLMError, loads_json_object
from app.providers.llm.http import post_json


class GeminiProvider:
    name = "gemini"
    _BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, *, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    @property
    def available(self) -> bool:
        return bool(settings.gemini_api_key)

    async def generate_json(self, system: str, user: str) -> dict[str, Any]:
        if not self.available:
            raise LLMError("Gemini : clé API absente (GEMINI_API_KEY).")
        url = f"{self._BASE}/{settings.gemini_model}:generateContent"
        data = await post_json(
            url,
            json_body={
                "system_instruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "response_mime_type": "application/json",
                },
            },
            headers={"x-goog-api-key": settings.gemini_api_key},
            client=self._client,
        )
        try:
            content = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Gemini : format de réponse inattendu.") from exc
        return loads_json_object(content)
