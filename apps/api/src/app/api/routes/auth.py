"""Endpoints d'authentification : login (JWT) et profil courant."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, SessionDep
from app.core.ratelimit import RateLimiter, get_login_rate_limiter
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import RefreshRequest, Token
from app.schemas.user import UserRead
from app.services import audit
from app.services import refresh_tokens as refresh_tokens_service
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
    access_token = create_access_token(subject=str(user.id), role=user.role.value)
    refresh_token, _ = await refresh_tokens_service.issue(session, user.id)
    await audit.record(session, action="login", user_id=user.id, ip_address=ip)
    await session.commit()
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserRead, summary="Profil de l'utilisateur connecté")
async def read_me(current_user: CurrentUser) -> User:
    """Renvoie les informations de l'utilisateur authentifié."""
    return current_user


@router.post("/refresh", response_model=Token, summary="Rafraîchir le jeton d'accès")
async def refresh(
    request: Request,
    body: RefreshRequest,
    session: SessionDep,
) -> Token:
    """Échange un refresh token valide contre un nouveau couple access/refresh.

    Rotation : l'ancien refresh token est immédiatement révoqué et remplacé.
    Un jeton déjà utilisé, révoqué ou expiré est rejeté (401) — l'appelant doit
    alors se reconnecter.
    """
    ip = request.client.host if request.client else "unknown"
    row = await refresh_tokens_service.get_valid(session, body.refresh_token)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide, révoqué ou expiré.",
        )

    user = await users_service.get_by_id(session, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide, révoqué ou expiré.",
        )

    new_refresh, _ = await refresh_tokens_service.rotate(session, row)
    access_token = create_access_token(subject=str(user.id), role=user.role.value)
    await audit.record(session, action="refresh", user_id=user.id, ip_address=ip)
    await session.commit()
    return Token(access_token=access_token, refresh_token=new_refresh)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Déconnexion (révocation du refresh token)",
)
async def logout(request: Request, body: RefreshRequest, session: SessionDep) -> None:
    """Révoque le refresh token fourni. Idempotent (silencieux si déjà invalide)."""
    ip = request.client.host if request.client else "unknown"
    row = await refresh_tokens_service.get_valid(session, body.refresh_token)
    if row is not None:
        await refresh_tokens_service.revoke(session, row)
        await audit.record(session, action="logout", user_id=row.user_id, ip_address=ip)
        await session.commit()
