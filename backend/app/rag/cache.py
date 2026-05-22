"""Redis exact-match query cache.

Key = SHA-256 of normalized (lowercase, collapsed whitespace) question + collection.
Non-streaming responses only — SSE streams are not cached.
"""
from __future__ import annotations

import hashlib
import json
import logging

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


def _key(question: str, collection: str) -> str:
    normalized = " ".join(question.strip().lower().split())
    digest = hashlib.sha256(f"{collection}:{normalized}".encode()).hexdigest()
    return f"rag:query:{digest}"


async def get_cached(redis: Redis, question: str, collection: str) -> dict | None:
    try:
        raw = await redis.get(_key(question, collection))
        if raw:
            logger.debug("Cache HIT collection=%s", collection)
            return json.loads(raw)
    except Exception as exc:
        logger.warning("Cache get error: %s", exc)
    return None


async def set_cached(
    redis: Redis,
    question: str,
    collection: str,
    payload: dict,
    ttl: int,
) -> None:
    try:
        await redis.setex(_key(question, collection), ttl, json.dumps(payload))
        logger.debug("Cache SET collection=%s ttl=%ds", collection, ttl)
    except Exception as exc:
        logger.warning("Cache set error: %s", exc)
