from __future__ import annotations
import logging
import time
from typing import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import QueryResponse, SourceDoc, StreamChunk
from app.ingestion.embedder import embed_query
from app.rag.retriever import retrieve
from app.rag.reranker import rerank
from app.rag.generator import generate_stream, generate
from app.models.db import QueryLog

logger = logging.getLogger(__name__)


async def query_stream(
    db: AsyncSession,
    question: str,
    collection: str = "general",
    user_id: str | None = None,
) -> AsyncIterator[StreamChunk]:
    """Full RAG pipeline with streaming. Yields StreamChunk objects."""
    start = time.perf_counter()

    # 1. Embed query
    query_embedding = await embed_query(question)

    # 2. Hybrid retrieval
    candidates = await retrieve(db, query_embedding, question, collection)
    if not candidates:
        yield StreamChunk(type="error", content="Aucun document pertinent trouvé.")
        return

    # 3. Rerank
    sources = await rerank(question, candidates)

    # 4. Stream generation
    full_answer = []
    async for token in generate_stream(question, sources):
        full_answer.append(token)
        yield StreamChunk(type="token", content=token)

    answer = "".join(full_answer)
    latency_ms = int((time.perf_counter() - start) * 1000)

    # 5. Send sources then audit log (done carries the log id for client feedback)
    yield StreamChunk(type="sources", sources=sources)
    log_id = await _log_query(db, user_id, question, answer, sources, latency_ms, collection)
    yield StreamChunk(type="done", query_log_id=log_id)


async def query(
    db: AsyncSession,
    question: str,
    collection: str = "general",
    user_id: str | None = None,
) -> QueryResponse:
    """Full RAG pipeline without streaming."""
    start = time.perf_counter()

    query_embedding = await embed_query(question)
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

    return QueryResponse(
        answer=answer,
        sources=sources,
        latency_ms=latency_ms,
        tokens_used=tokens_used,
    )


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
