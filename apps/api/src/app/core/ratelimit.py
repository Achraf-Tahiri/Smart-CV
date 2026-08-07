"""Limitation du taux de tentatives de connexion (anti-brute-force).

Compte les échecs par clé (IP) dans une fenêtre glissante. **Fail-open** : si
Redis est indisponible, on n'empêche jamais la connexion (la disponibilité prime).
"""

from typing import Protocol

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("ratelimit")

_PREFIX = "ratelimit:login:"


class RateLimiter(Protocol):
    async def too_many(self, key: str) -> bool:
        """Vrai si la clé a déjà atteint la limite d'échecs."""
        ...

    async def register_failure(self, key: str) -> None:
        """Enregistre un échec pour la clé."""
        ...

    async def clear(self, key: str) -> None:
        """Réinitialise le compteur (connexion réussie)."""
        ...


class RedisRateLimiter:
    """Compteur d'échecs dans Redis (INCR + EXPIRE). Fail-open en cas d'erreur."""

    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self._max = max_attempts
        self._window = window_seconds

    async def _redis(self):
        # Réutilise le pool Redis (le même que la file de jobs).
        from app.core.queue import get_pool

        return await get_pool()

    async def too_many(self, key: str) -> bool:
        try:
            value = await (await self._redis()).get(_PREFIX + key)
            return value is not None and int(value) >= self._max
        except Exception as exc:  # Redis indisponible -> on laisse passer
            logger.warning("ratelimit_unavailable", error=str(exc))
            return False

    async def register_failure(self, key: str) -> None:
        try:
            redis = await self._redis()
            full = _PREFIX + key
            count = await redis.incr(full)
            if count == 1:
                await redis.expire(full, self._window)
        except Exception as exc:
            logger.warning("ratelimit_unavailable", error=str(exc))

    async def clear(self, key: str) -> None:
        try:
            await (await self._redis()).delete(_PREFIX + key)
        except Exception:
            pass


class InMemoryRateLimiter:
    """Version mémoire (tests / fallback). Ignore la fenêtre temporelle."""

    def __init__(self, max_attempts: int, window_seconds: int = 0) -> None:
        self._max = max_attempts
        self._counts: dict[str, int] = {}

    async def too_many(self, key: str) -> bool:
        return self._counts.get(key, 0) >= self._max

    async def register_failure(self, key: str) -> None:
        self._counts[key] = self._counts.get(key, 0) + 1

    async def clear(self, key: str) -> None:
        self._counts.pop(key, None)


def get_login_rate_limiter() -> RateLimiter:
    """Dépendance FastAPI : le limiteur de login (Redis). Surchargé en test."""
    return RedisRateLimiter(settings.login_max_attempts, settings.login_window_seconds)
