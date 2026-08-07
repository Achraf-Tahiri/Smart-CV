"""Fournisseur LLM : Hugging Face (routeur compatible OpenAI).

⚠️ L'inférence gratuite HF est la moins fiable (disponibilité variable des
modèles) : c'est le dernier recours de la cascade. On ne force pas de JSON mode
(support inégal) ; on s'appuie sur le prompt + le parsing tolérant.
"""

from typing import Any

import httpx

from app.core.config import settings
from app.providers.llm.base import LLMError, loads_json_object
from app.providers.llm.http import post_json


class HFProvider:
    name = "hf"
    _URL = "https://router.huggingface.co/v1/chat/completions"

    def __init__(self, *, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    @property
    def available(self) -> bool:
        return bool(settings.hf_api_token)

    async def generate_json(self, system: str, user: str) -> dict[str, Any]:
        if not self.available:
            raise LLMError("Hugging Face : jeton absent (HF_API_TOKEN).")
        data = await post_json(
            self._URL,
            json_body={
                "model": settings.hf_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.1,
                "max_tokens": 2000,
                "stream": False,
            },
            headers={"Authorization": f"Bearer {settings.hf_api_token}"},
            client=self._client,
        )
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Hugging Face : format de réponse inattendu.") from exc
        return loads_json_object(content)
