"""Connexion asynchrone à la base de données (SQLAlchemy 2.0)."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# Moteur async (driver asyncpg). La connexion est ouverte à la demande (lazy),
# donc l'API peut démarrer même si la base n'est pas encore joignable.
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,  # teste la connexion avant usage (évite les connexions mortes)
)

# Fabrique de sessions async, à injecter dans les endpoints.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dépendance FastAPI : fournit une session DB par requête."""
    async with AsyncSessionLocal() as session:
        yield session
