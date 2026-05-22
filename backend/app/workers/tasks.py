from __future__ import annotations

import asyncio

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "rag_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        # Re-ingest all sources every 4 hours
        "refresh-sources": {
            "task": "app.workers.tasks.refresh_all_sources",
            "schedule": 14400,  # 4h in seconds
        },
    },
)


def _run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@celery_app.task(name="app.workers.tasks.ingest_pdf", bind=True, max_retries=3)
def ingest_pdf_task(self, file_path: str, collection: str = "general"):
    from app.core.database import AsyncSessionLocal
    from app.ingestion.pdf_loader import PDFLoader

    async def _run():
        async with AsyncSessionLocal() as db:
            loader = PDFLoader(file_path)
            return await loader.ingest(db, collection)

    try:
        return _run_async(_run())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60) from exc


@celery_app.task(name="app.workers.tasks.ingest_confluence", bind=True, max_retries=3)
def ingest_confluence_task(self, space_key: str, collection: str = "general"):
    from app.core.database import AsyncSessionLocal
    from app.ingestion.confluence import ConfluenceLoader

    async def _run():
        async with AsyncSessionLocal() as db:
            loader = ConfluenceLoader(space_key)
            return await loader.ingest(db, collection)

    try:
        return _run_async(_run())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120) from exc


@celery_app.task(name="app.workers.tasks.refresh_all_sources")
def refresh_all_sources():
    """Periodic task: re-trigger ingestion for all registered sources."""
    # TODO: load source registry from DB and dispatch individual tasks
    pass
