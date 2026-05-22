from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.db import Document, IngestionJob
from app.ingestion.chunker import chunk_text, Chunk
from app.ingestion.embedder import embed_texts, compute_checksum
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class BaseLoader(ABC):
    source_type: str = ""

    @abstractmethod
    async def load(self) -> list[tuple[str, dict]]:
        """Return list of (text, metadata) tuples."""

    async def ingest(self, db: AsyncSession, collection: str = "general") -> int:
        """Load, chunk, embed and store. Returns number of new chunks inserted."""
        job = IngestionJob(
            source_type=self.source_type,
            source_id=self._source_id(),
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(job)
        await db.commit()

        try:
            raw_docs = await self.load()
            chunks: list[Chunk] = []
            for text, meta in raw_docs:
                chunks.extend(chunk_text(text, meta))

            new_count = await self._store_chunks(db, chunks, collection)

            job.status = "done"
            job.chunks_count = new_count
            job.finished_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info("%s ingestion done: %d new chunks", self.source_type, new_count)
            return new_count

        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            job.finished_at = datetime.now(timezone.utc)
            await db.commit()
            raise

    async def _store_chunks(self, db: AsyncSession, chunks: list[Chunk], collection: str) -> int:
        if not chunks:
            return 0

        contents = [c.content for c in chunks]
        checksums = [compute_checksum(c) for c in contents]

        # Filter already-existing chunks by checksum (deduplication)
        existing = set(
            row[0]
            for row in (
                await db.execute(select(Document.checksum).where(Document.checksum.in_(checksums)))
            ).all()
        )

        new_chunks = [(chunk, cs) for chunk, cs in zip(chunks, checksums) if cs not in existing]
        if not new_chunks:
            return 0

        embeddings = await embed_texts([c.content for c, _ in new_chunks])

        docs = [
            Document(
                source_type=self.source_type,
                source_id=chunk.metadata.get("source_id", ""),
                title=chunk.metadata.get("title"),
                content=chunk.content,
                checksum=cs,
                embedding=emb,
                metadata_=chunk.metadata,
                collection=collection,
            )
            for (chunk, cs), emb in zip(new_chunks, embeddings)
        ]
        db.add_all(docs)
        await db.commit()
        return len(docs)

    def _source_id(self) -> str:
        return ""
