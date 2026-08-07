"""Fixtures partagées des tests.

Deux familles de tests coexistent :
- **unitaires** (fonctions pures) : n'utilisent aucune fixture DB → aucune base requise ;
- **d'intégration** (endpoints) : utilisent `client` / `db_session`, branchés sur une
  base Postgres de test dédiée (`<db>_test`) créée automatiquement.

Isolation : la base de test est préparée une fois (extension pgvector + tables), puis
chaque test d'intégration démarre sur des tables vidées (`TRUNCATE`).

On teste l'API en async via httpx `ASGITransport` (pas de serveur réseau).
"""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app import models  # noqa: F401  (enregistre toutes les tables dans Base.metadata)
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_session
from app.main import create_app
from app.models.enums import UserRole
from app.models.user import User
from app.providers.storage import get_storage
from app.providers.storage.memory import InMemoryStorageProvider
from app.schemas.user import UserCreate
from app.services import users as users_service

# --- URLs dérivées de la config : base de test = <db>_test ---
_url = make_url(settings.database_url)
_TEST_DB_NAME = f"{_url.database}_test"
TEST_DATABASE_URL = _url.set(database=_TEST_DB_NAME).render_as_string(hide_password=False)
_ADMIN_URL = _url.set(database="postgres").render_as_string(hide_password=False)


async def _prepare_database() -> None:
    """Crée la base de test (si absente), l'extension pgvector et les tables."""
    # 1) Créer la base de test via la base de maintenance 'postgres' (hors transaction).
    admin_engine = create_async_engine(_ADMIN_URL, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    try:
        async with admin_engine.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": _TEST_DB_NAME}
            )
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{_TEST_DB_NAME}"'))
    finally:
        await admin_engine.dispose()

    # 2) Dans la base de test : extension vecteur + schéma.
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def _prepared_db() -> bool:
    """Prépare la base de test une seule fois pour toute la session."""
    asyncio.run(_prepare_database())
    return True


@pytest.fixture
def anyio_backend() -> str:
    """Backend async utilisé par les tests."""
    return "asyncio"


@pytest.fixture
async def db_engine(_prepared_db):
    """Moteur async sur la base de test (NullPool : pas de connexion partagée entre boucles)."""
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest.fixture
async def _clean(db_engine) -> AsyncIterator[None]:
    """Vide toutes les tables avant le test (isolation)."""
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    async with db_engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
async def db_session(db_engine, _clean) -> AsyncIterator[AsyncSession]:
    """Session DB directe (pour préparer des données dans les tests)."""
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest.fixture
def fake_storage() -> InMemoryStorageProvider:
    """Stockage en mémoire (pas de MinIO requis en test)."""
    return InMemoryStorageProvider()


@pytest.fixture
async def app(db_engine, _clean, fake_storage) -> FastAPI:
    """Application FastAPI de test (DB + stockage pointés sur les doubles).

    Les tests peuvent surcharger d'autres dépendances (ex. get_llm) via
    `app.dependency_overrides` avant d'émettre des requêtes.
    """
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    application = create_app()

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        async with maker() as session:
            yield session

    application.dependency_overrides[get_session] = _override_get_session
    application.dependency_overrides[get_storage] = lambda: fake_storage
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Client HTTP async branché sur l'app de test."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def make_user(db_session) -> Callable[..., Awaitable[tuple[User, str]]]:
    """Fabrique d'utilisateur pour les tests. Retourne (user, mot_de_passe_en_clair)."""

    async def _make(
        email: str = "user@example.com",
        password: str = "password123",
        role: UserRole = UserRole.admin,
        full_name: str | None = None,
    ) -> tuple[User, str]:
        user = await users_service.create_user(
            db_session,
            UserCreate(email=email, password=password, role=role, full_name=full_name),
        )
        await db_session.commit()
        return user, password

    return _make


async def login(client: AsyncClient, email: str, password: str) -> dict[str, str]:
    """Se connecte et renvoie l'en-tête Authorization prêt à l'emploi."""
    resp = await client.post("/api/v1/auth/login", data={"username": email, "password": password})
    resp.raise_for_status()
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
