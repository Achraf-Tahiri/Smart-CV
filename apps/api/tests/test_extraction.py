"""Tests de l'extraction structurée (schéma + réessai), sans réseau."""

import pytest

from app.providers.llm.base import LLMError
from app.providers.llm.fake import FakeLLMProvider
from app.schemas.extraction import CVExtraction
from app.services.extraction import build_prompt, extract_cv

pytestmark = pytest.mark.anyio

VALID = {
    "prenom": "Alex",
    "nom": "Exemple",
    "email": "a@example.com",
    "secteur": "Informatique / Tech",
    "experiences": [
        {"poste": "Dev", "entreprise": "X", "date_debut": "2020-01", "date_fin": "PRESENT"}
    ],
    "hard_skills": ["Python"],
    "langues": ["Français (natif)"],
}


async def test_extract_cv_valid():
    result = await extract_cv(FakeLLMProvider(VALID), "texte du cv")
    assert isinstance(result, CVExtraction)
    assert result.prenom == "Alex"
    assert result.secteur == "Informatique / Tech"
    assert result.experiences[0].date_fin == "PRESENT"


async def test_extract_cv_coerces_unknown_secteur():
    result = await extract_cv(FakeLLMProvider({"secteur": "Cryptomonnaie"}), "cv")
    assert result.secteur == "Autre"


async def test_extract_cv_empty_text_raises():
    with pytest.raises(LLMError):
        await extract_cv(FakeLLMProvider(VALID), "   ")


def test_build_prompt_contains_sectors_and_text():
    prompt = build_prompt("MON CV ICI")
    assert "Informatique / Tech" in prompt
    assert "MON CV ICI" in prompt


async def test_extract_cv_retries_then_succeeds():
    """1er JSON non conforme au schéma -> réessai -> 2e conforme."""

    class SequencedLLM:
        name = "seq"

        def __init__(self) -> None:
            self.n = 0

        @property
        def available(self) -> bool:
            return True

        async def generate_json(self, system: str, user: str) -> dict:
            self.n += 1
            if self.n == 1:
                return {"experiences": "pas une liste"}  # invalide
            return VALID

    llm = SequencedLLM()
    result = await extract_cv(llm, "cv")
    assert result.prenom == "Alex"
    assert llm.n == 2  # il a bien fallu 2 tentatives
