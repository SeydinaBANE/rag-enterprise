"""Rate limiting par utilisateur via Redis (compteur INCR + EXPIRE).

Implémenté comme dépendance FastAPI — compatible avec l'injection de dépendances
et n'altère pas la signature des handlers (évite le problème du décorateur slowapi).
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.redis import get_redis
from app.core.security import decode_token

settings = get_settings()


def _rate_limit_key(request: Request) -> str:
    """Clé Redis : user UUID si authentifié, sinon adresse IP."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        payload = decode_token(auth[7:])
        if payload and payload.get("type") == "access":
            return f"rl:user:{payload['sub']}"
    forwarded_for = request.headers.get("X-Forwarded-For")
    ip = forwarded_for.split(",")[0].strip() if forwarded_for else request.client.host
    return f"rl:ip:{ip}"


async def check_query_rate_limit(
    request: Request,
    redis: Redis = Depends(get_redis),
) -> None:
    """Dépendance FastAPI : lève 429 si le quota par minute est dépassé."""
    try:
        key = _rate_limit_key(request)
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)
        if count > settings.rate_limit_query_per_minute:
            raise HTTPException(
                status_code=429,
                detail=f"Trop de requêtes — limite : {settings.rate_limit_query_per_minute}/minute",
            )
    except HTTPException:
        raise
    except Exception:
        pass
