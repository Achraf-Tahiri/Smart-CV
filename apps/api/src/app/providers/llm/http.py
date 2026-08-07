"""Petit utilitaire HTTP partagé par les fournisseurs LLM (httpx async)."""

from typing import Any

import httpx

from app.core.config import settings
from app.providers.llm.base import LLMError


async def post_json(
    url: str,
    *,
    json_body: dict[str, Any],
    headers: dict[str, str] | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """POST JSON et renvoie la réponse JSON. Lève `LLMError` sur toute erreur HTTP.

    Si `client` est fourni (tests : `httpx.MockTransport`), il est réutilisé et
    NON fermé ; sinon un client éphémère est créé puis fermé.
    """
    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=settings.llm_timeout_seconds)
    try:
        response = await client.post(url, json=json_body, headers=headers)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        raise LLMError(f"HTTP {exc.response.status_code}: {exc.response.text[:200]}") from exc
    except httpx.HTTPError as exc:
        raise LLMError(f"Erreur réseau : {exc}") from exc
    finally:
        if own_client:
            await client.aclose()
