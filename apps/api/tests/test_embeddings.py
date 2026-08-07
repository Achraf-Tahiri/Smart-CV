"""Tests du fournisseur d'embeddings déterministe."""

import math

import pytest

from app.providers.embeddings.deterministic import DeterministicEmbeddingProvider

pytestmark = pytest.mark.anyio


async def test_dimension_and_norm():
    provider = DeterministicEmbeddingProvider(dimension=768)
    vec = await provider.embed_query("ingénieur data")
    assert provider.dimension == 768
    assert len(vec) == 768
    assert math.isclose(math.sqrt(sum(v * v for v in vec)), 1.0, rel_tol=1e-6)


async def test_deterministic_same_text_same_vector():
    provider = DeterministicEmbeddingProvider()
    assert await provider.embed_query("Python") == await provider.embed_query("Python")


async def test_different_text_different_vector():
    provider = DeterministicEmbeddingProvider()
    assert await provider.embed_query("Python") != await provider.embed_query("Java")


async def test_embed_documents_length():
    provider = DeterministicEmbeddingProvider()
    vectors = await provider.embed_documents(["a", "b", "c"])
    assert len(vectors) == 3
    assert all(len(v) == provider.dimension for v in vectors)
