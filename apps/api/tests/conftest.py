"""Fixtures partagées des tests.

On teste l'API en async, sans lancer de serveur réseau : httpx parle
directement à l'application ASGI via ASGITransport. C'est le pattern moderne
(sans dépréciation) et celui qu'on réutilisera pour les endpoints async.
"""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def anyio_backend() -> str:
    """Backend async utilisé par les tests."""
    return "asyncio"


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Client HTTP async branché sur une instance neuve de l'application."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
