from __future__ import annotations

import asyncio
import hashlib
import logging
from functools import lru_cache

from fastembed import TextEmbedding

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@lru_cache(maxsize=1)
def _get_model() -> TextEmbedding:
    logger.info("Loading embedding model %s (first call — downloads if needed)", settings.embedding_model)
    return TextEmbedding(model_name=settings.embedding_model)


def compute_checksum(content: str) -> str:
    return hashlib.md5(content.encode()).hexdigest()


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts using local fastembed model (runs in thread pool to avoid blocking)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _embed_sync, texts)


def _embed_sync(texts: list[str]) -> list[list[float]]:
    model = _get_model()
    embeddings = list(model.embed(texts, batch_size=64))
    return [emb.tolist() for emb in embeddings]


async def embed_query(text: str) -> list[float]:
    results = await embed_texts([text])
    return results[0]
