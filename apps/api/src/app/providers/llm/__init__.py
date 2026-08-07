"""Fournisseurs LLM — point d'entrée + injection FastAPI.

`get_llm()` construit la cascade à partir de `LLM_PROVIDER_ORDER`. En test, la
dépendance est surchargée par un `FakeLLMProvider`.
"""

from functools import lru_cache

from app.core.config import settings
from app.providers.llm.base import LLMError, LLMProvider
from app.providers.llm.cascade import CascadeLLMProvider
from app.providers.llm.gemini import GeminiProvider
from app.providers.llm.groq import GroqProvider
from app.providers.llm.hf import HFProvider

__all__ = ["LLMError", "LLMProvider", "get_llm"]

# Nom (dans LLM_PROVIDER_ORDER) -> classe de fournisseur.
_REGISTRY: dict[str, type] = {
    "groq": GroqProvider,
    "gemini": GeminiProvider,
    "hf": HFProvider,
}


@lru_cache
def _default_llm() -> CascadeLLMProvider:
    providers = [_REGISTRY[name]() for name in settings.llm_order if name in _REGISTRY]
    return CascadeLLMProvider(providers)


def get_llm() -> LLMProvider:
    """Dépendance FastAPI : la cascade LLM. Surchargée dans les tests."""
    return _default_llm()
