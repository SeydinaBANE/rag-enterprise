from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.db import Document
from app.models.schemas import SourceDoc

logger = logging.getLogger(__name__)
settings = get_settings()


async def retrieve(
    db: AsyncSession,
    query_embedding: list[float],
    query_text: str,
    collection: str = "general",
    top_k: int | None = None,
) -> list[SourceDoc]:
    """Hybrid search: dense cosine + BM25 sparse, fused with Reciprocal Rank Fusion."""
    k = top_k or settings.retrieval_top_k

    dense_results = await _dense_search(db, query_embedding, collection, k)
    sparse_results = await _sparse_search(db, query_text, collection, k)

    fused = _reciprocal_rank_fusion(dense_results, sparse_results, k=k)
    return fused


async def _dense_search(
    db: AsyncSession,
    embedding: list[float],
    collection: str,
    k: int,
) -> list[tuple[Document, float]]:
    vec_str = "[" + ",".join(str(v) for v in embedding) + "]"
    stmt = text(
        """
        SELECT id, source_type, source_id, title, content, metadata,
               1 - (embedding <=> CAST(:vec AS vector)) AS score
        FROM documents
        WHERE collection = :collection
          AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:vec AS vector)
        LIMIT :k
        """
    )
    rows = await db.execute(stmt, {"vec": vec_str, "collection": collection, "k": k})
    results = []
    for row in rows.mappings():
        doc = Document(
            id=row["id"],
            source_type=row["source_type"],
            source_id=row["source_id"],
            title=row["title"],
            content=row["content"],
            metadata_=row["metadata"] or {},
        )
        results.append((doc, float(row["score"])))
    return results


async def _sparse_search(
    db: AsyncSession,
    query: str,
    collection: str,
    k: int,
) -> list[tuple[Document, float]]:
    stmt = text(
        """
        SELECT id, source_type, source_id, title, content, metadata,
               ts_rank(to_tsvector('french', content), plainto_tsquery('french', :query)) AS score
        FROM documents
        WHERE collection = :collection
          AND to_tsvector('french', content) @@ plainto_tsquery('french', :query)
        ORDER BY score DESC
        LIMIT :k
        """
    )
    rows = await db.execute(stmt, {"query": query, "collection": collection, "k": k})
    results = []
    for row in rows.mappings():
        doc = Document(
            id=row["id"],
            source_type=row["source_type"],
            source_id=row["source_id"],
            title=row["title"],
            content=row["content"],
            metadata_=row["metadata"] or {},
        )
        results.append((doc, float(row["score"])))
    return results


def _reciprocal_rank_fusion(
    dense: list[tuple[Document, float]],
    sparse: list[tuple[Document, float]],
    k: int = 60,
) -> list[SourceDoc]:
    """RRF: score = sum(1 / (rank + k)) across result lists."""
    rrf_scores: dict[str, float] = {}
    doc_map: dict[str, Document] = {}

    for rank, (doc, _) in enumerate(dense, start=1):
        key = str(doc.id)
        rrf_scores[key] = rrf_scores.get(key, 0) + 1 / (rank + k)
        doc_map[key] = doc

    for rank, (doc, _) in enumerate(sparse, start=1):
        key = str(doc.id)
        rrf_scores[key] = rrf_scores.get(key, 0) + 1 / (rank + k)
        doc_map[key] = doc

    sorted_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)

    results = []
    for doc_id in sorted_ids[:k]:
        doc = doc_map[doc_id]
        score = rrf_scores[doc_id]
        meta = doc.metadata_ or {}
        results.append(SourceDoc(
            id=doc_id,
            title=doc.title,
            source_type=doc.source_type,
            source_id=doc.source_id,
            content_excerpt=doc.content[:300] + "..." if len(doc.content) > 300 else doc.content,
            score=round(score, 4),
            url=meta.get("url"),
        ))

    return results
