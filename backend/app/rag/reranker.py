from __future__ import annotations
import logging
import cohere
from app.models.schemas import SourceDoc
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client: cohere.AsyncClient | None = None


def _get_cohere() -> cohere.AsyncClient | None:
    global _client
    if not settings.cohere_api_key:
        return None
    if _client is None:
        _client = cohere.AsyncClient(settings.cohere_api_key)
    return _client


async def rerank(query: str, docs: list[SourceDoc], top_n: int | None = None) -> list[SourceDoc]:
    """Rerank with Cohere. Falls back to original order if API key not set."""
    n = top_n or settings.rerank_top_n
    client = _get_cohere()

    if client is None:
        logger.debug("Cohere not configured — using cosine ranking")
        return docs[:n]

    try:
        response = await client.rerank(
            model="rerank-v3.5",
            query=query,
            documents=[d.content_excerpt for d in docs],
            top_n=n,
        )
        reranked = [docs[r.index] for r in response.results]
        for i, (result, doc) in enumerate(zip(response.results, reranked)):
            doc.score = round(result.relevance_score, 4)
        logger.debug("Reranked %d → %d docs", len(docs), len(reranked))
        return reranked

    except Exception as exc:
        logger.warning("Cohere rerank failed (%s) — falling back to original order", exc)
        return docs[:n]
