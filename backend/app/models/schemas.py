from __future__ import annotations
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    collection: str = "general"
    stream: bool = True


class SourceDoc(BaseModel):
    id: str
    title: str | None
    source_type: str
    source_id: str
    content_excerpt: str
    score: float
    url: str | None = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceDoc]
    latency_ms: int
    tokens_used: int | None = None


class StreamChunk(BaseModel):
    type: str  # "token" | "sources" | "done" | "error"
    content: str | None = None
    sources: list[SourceDoc] | None = None


class IngestResponse(BaseModel):
    job_id: str
    status: str
    chunks_count: int = 0
    message: str


class FeedbackRequest(BaseModel):
    query_log_id: str
    feedback: int = Field(..., ge=-1, le=1)


class HealthResponse(BaseModel):
    status: str
    db: str
    redis: str
    version: str = "1.0.0"
