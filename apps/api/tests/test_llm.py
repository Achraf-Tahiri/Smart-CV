"""Tests de la couche LLM : parsing JSON, cascade, providers (HTTP mocké)."""

import httpx
import pytest

from app.core.config import settings
from app.providers.llm.base import LLMError, loads_json_object
from app.providers.llm.cascade import CascadeLLMProvider
from app.providers.llm.fake import FakeLLMProvider
from app.providers.llm.gemini import GeminiProvider
from app.providers.llm.groq import GroqProvider

pytestmark = pytest.mark.anyio


# --- loads_json_object (synchrone) ---


def test_loads_json_object_direct():
    assert loads_json_object('{"a": 1}') == {"a": 1}


def test_loads_json_object_surrounded_by_text():
    assert loads_json_object('Voici: ```json\n{"a": 1}\n``` fin') == {"a": 1}


def test_loads_json_object_invalid_raises():
    with pytest.raises(LLMError):
        loads_json_object("pas de json ici")


def test_loads_json_object_not_an_object_raises():
    with pytest.raises(LLMError):
        loads_json_object("[1, 2, 3]")


# --- Cascade ---


async def test_cascade_returns_first_available_success():
    unavailable = FakeLLMProvider(available=False)
    winner = FakeLLMProvider({"ok": 1})
    never = FakeLLMProvider({"no": 0})
    cascade = CascadeLLMProvider([unavailable, winner, never])

    assert await cascade.generate_json("s", "u") == {"ok": 1}
    assert winner.calls  # appelé
    assert not never.calls  # jamais atteint


async def test_cascade_skips_failing_provider():
    cascade = CascadeLLMProvider([FakeLLMProvider(fail=True), FakeLLMProvider({"ok": 1})])
    assert await cascade.generate_json("s", "u") == {"ok": 1}


async def test_cascade_all_fail_raises():
    with pytest.raises(LLMError):
        await CascadeLLMProvider([FakeLLMProvider(fail=True)]).generate_json("s", "u")


async def test_cascade_none_configured():
    cascade = CascadeLLMProvider([FakeLLMProvider(available=False)])
    assert cascade.available is False
    with pytest.raises(LLMError):
        await cascade.generate_json("s", "u")


# --- Providers réels (HTTP mocké via httpx.MockTransport) ---


async def test_groq_provider_parses_content(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(
            200, json={"choices": [{"message": {"content": '{"prenom": "Alex"}'}}]}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = GroqProvider(client=client)
        assert provider.available is True
        assert await provider.generate_json("sys", "user") == {"prenom": "Alex"}


async def test_groq_unavailable_without_key(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "")
    provider = GroqProvider()
    assert provider.available is False
    with pytest.raises(LLMError):
        await provider.generate_json("s", "u")


async def test_groq_http_error_raises(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "k")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(LLMError):
            await GroqProvider(client=client).generate_json("s", "u")


async def test_gemini_provider_parses_content(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "gkey")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": '{"nom": "X"}'}]}}]}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await GeminiProvider(client=client).generate_json("s", "u") == {"nom": "X"}
