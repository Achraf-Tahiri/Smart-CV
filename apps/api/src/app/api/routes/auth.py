"""Endpoints d'authentification : login (JWT) et profil courant."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, SessionDep
from app.core.ratelimit import RateLimiter, get_login_rate_limiter
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import Token
from app.schemas.user import UserRead
from app.services import audit
from app.services import users as users_service

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=Token, summary="Connexion (OAuth2 password flow)")
async def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
    limiter: Annotated[RateLimiter, Depends(get_login_rate_limiter)],
) -> Token:
    """Vérifie les identifiants et renvoie un jeton d'accès JWT.

    Le champ `username` du formulaire OAuth2 contient l'email.
    Protégé contre le brute-force (blocage temporaire par IP après trop d'échecs).
    Chaque tentative (réussie ou non) est tracée dans le journal d'audit.
    """
    ip = request.client.host if request.client else "unknown"

    if await limiter.too_many(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de tentatives de connexion. Réessaie dans quelques minutes.",
        )

    user = await users_service.authenticate(session, form.username, form.password)

    if user is None:
        await limiter.register_failure(ip)
        await audit.record(
            session,
            action="login_failed",
            details={"email": form.username},
            ip_address=ip,
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    await limiter.clear(ip)
    token = create_access_token(subject=str(user.id), role=user.role.value)
    await audit.record(session, action="login", user_id=user.id, ip_address=ip)
    await session.commit()
    return Token(access_token=token)


@router.get("/me", response_model=UserRead, summary="Profil de l'utilisateur connecté")
async def read_me(current_user: CurrentUser) -> User:
    """Renvoie les informations de l'utilisateur authentifié."""
    return current_user
