"""Service métier : utilisateurs (lecture, création, authentification).

Convention : les fonctions de service NE committent PAS. L'appelant (endpoint,
script) décide de la frontière de transaction. Ici on `flush` quand on a besoin
de l'identifiant généré, sans valider définitivement.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    """Retourne l'utilisateur d'un email (insensible à la casse), ou None."""
    result = await session.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Retourne l'utilisateur d'un identifiant, ou None."""
    return await session.get(User, user_id)


async def create_user(session: AsyncSession, data: UserCreate) -> User:
    """Crée un utilisateur (email normalisé en minuscules, mot de passe haché)."""
    user = User(
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
    )
    session.add(user)
    await session.flush()  # renseigne user.id sans committer
    return user


async def authenticate(session: AsyncSession, email: str, password: str) -> User | None:
    """Vérifie email + mot de passe. Retourne l'utilisateur si OK et actif, sinon None."""
    user = await get_by_email(session, email)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
