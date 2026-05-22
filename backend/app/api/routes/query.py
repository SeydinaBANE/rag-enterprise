from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_user, CurrentUser
from app.models.schemas import QueryRequest, QueryResponse, FeedbackRequest
from app.rag.pipeline import query_stream, query
from app.models.db import QueryLog
from sqlalchemy import select, update
import uuid

router = APIRouter()


@router.post("/query")
async def handle_query(
    req: QueryRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    if not user.can_access(req.collection):
        raise HTTPException(status_code=403, detail=f"Accès à la collection '{req.collection}' non autorisé")

    if req.stream:
        return StreamingResponse(
            _sse_stream(db, req, user.id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    else:
        result = await query(db, req.question, req.collection, user.id)
        return result


async def _sse_stream(db: AsyncSession, req: QueryRequest, user_id: str):
    async for chunk in query_stream(db, req.question, req.collection, user_id):
        data = chunk.model_dump_json(exclude_none=True)
        yield f"data: {data}\n\n"


@router.post("/query/feedback")
async def submit_feedback(
    req: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        log_id = uuid.UUID(req.query_log_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID invalide")

    stmt = (
        update(QueryLog)
        .where(QueryLog.id == log_id)
        .values(feedback=req.feedback)
    )
    await db.execute(stmt)
    await db.commit()
    return {"status": "ok"}
