from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user
from app.core.database import get_db
from app.core.metrics import ACTIVE_STREAMS, FEEDBACK_TOTAL, QUERY_LATENCY, QUERY_TOTAL, TOKENS_USED
from app.models.db import QueryLog
from app.models.schemas import FeedbackRequest, QueryRequest
from app.rag.pipeline import query, query_stream

router = APIRouter()


@router.post("/query")
async def handle_query(
    req: QueryRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    if not user.can_access(req.collection):
        raise HTTPException(status_code=403, detail=f"Accès à la collection '{req.collection}' non autorisé")

    QUERY_TOTAL.labels(collection=req.collection, user_role=user.role).inc()

    if req.stream:
        return StreamingResponse(
            _sse_stream(db, req, user),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    else:
        t0 = time.perf_counter()
        result = await query(db, req.question, req.collection, user.id)
        QUERY_LATENCY.labels(collection=req.collection).observe(time.perf_counter() - t0)
        if hasattr(result, "tokens_used") and result.tokens_used:
            TOKENS_USED.labels(collection=req.collection).inc(result.tokens_used)
        return result


async def _sse_stream(db: AsyncSession, req: QueryRequest, user: CurrentUser):
    ACTIVE_STREAMS.inc()
    t0 = time.perf_counter()
    try:
        async for chunk in query_stream(db, req.question, req.collection, user.id):
            if chunk.type == "done":
                QUERY_LATENCY.labels(collection=req.collection).observe(time.perf_counter() - t0)
            data = chunk.model_dump_json(exclude_none=True)
            yield f"data: {data}\n\n"
    finally:
        ACTIVE_STREAMS.dec()


@router.post("/query/feedback")
async def submit_feedback(
    req: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        log_id = uuid.UUID(req.query_log_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="ID invalide") from exc

    stmt = (
        update(QueryLog)
        .where(QueryLog.id == log_id)
        .values(feedback=req.feedback)
    )
    await db.execute(stmt)
    await db.commit()

    label = "positive" if req.feedback == 1 else "negative"
    FEEDBACK_TOTAL.labels(value=label).inc()

    return {"status": "ok"}
