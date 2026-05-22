from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.ingestion.embedder import embed_query
from app.models.db import QueryLog
from app.models.schemas import QueryResponse, SourceDoc, StreamChunk
from app.rag.cache import get_cached, set_cached
from app.rag.generator import generate, generate_stream
from app.rag.reranker import rerank
from app.rag.retriever import retrieve

logger = logging.getLogger(__name__)
settings = get_settings()


async def _get_query_embedding(question: str) -> list[float]:
    if settings.hyde_enabled:
        from app.rag.hyde import hyde_embed
        return await hyde_embed(question)
    return await embed_query(question)


async def query_stream(
    db: AsyncSession,
    question: str,
    collection: str = "general",
    user_id: str | None = None,
    redis: Redis | None = None,
) -> AsyncIterator[StreamChunk]:
    """Full RAG pipeline with streaming. SSE responses are not cached."""
    start = time.perf_counter()

    query_embedding = await _get_query_embedding(question)

    candidates = await retrieve(db, query_embedding, question, collection)
    if not candidates:
        yield StreamChunk(type="error", content="Aucun document pertinent trouvé.")
        return

    sources = await rerank(question, candidates)

    full_answer = []
    async for token in generate_stream(question, sources):
        full_answer.append(token)
        yield StreamChunk(type="token", content=token)

    answer = "".join(full_answer)
    latency_ms = int((time.perf_counter() - start) * 1000)

    yield StreamChunk(type="sources", sources=sources)
    log_id = await _log_query(db, user_id, question, answer, sources, latency_ms, collection)
    yield StreamChunk(type="done", query_log_id=log_id)


async def query(
    db: AsyncSession,
    question: str,
    collection: str = "general",
    user_id: str | None = None,
    redis: Redis | None = None,
) -> QueryResponse:
    """Full RAG pipeline without streaming. Checks and populates Redis cache."""
    if redis is not None:
        cached = await get_cached(redis, question, collection)
        if cached:
            return QueryResponse(**cached)

    start = time.perf_counter()

    query_embedding = await _get_query_embedding(question)
    candidates = await retrieve(db, query_embedding, question, collection)

    if not candidates:
        return QueryResponse(
            answer="Aucun document pertinent trouvé pour répondre à cette question.",
            sources=[],
            latency_ms=0,
        )

    sources = await rerank(question, candidates)
    answer, tokens_used = await generate(question, sources)
    latency_ms = int((time.perf_counter() - start) * 1000)

    await _log_query(db, user_id, question, answer, sources, latency_ms, collection, tokens_used)

    result = QueryResponse(answer=answer, sources=sources, latency_ms=latency_ms, tokens_used=tokens_used)

    if redis is not None:
        await set_cached(redis, question, collection, result.model_dump(), settings.cache_ttl_seconds)

    return result


async def _log_query(
    db: AsyncSession,
    user_id: str | None,
    question: str,
    answer: str,
    sources: list[SourceDoc],
    latency_ms: int,
    collection: str,
    tokens_used: int | None = None,
) -> str:
    log = QueryLog(
        user_id=user_id,
        question=question,
        answer=answer,
        sources=[s.model_dump() for s in sources],
        latency_ms=latency_ms,
        tokens_used=tokens_used,
        collection=collection,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    logger.info("Query logged: latency=%dms sources=%d id=%s", latency_ms, len(sources), log.id)
    return str(log.id)
