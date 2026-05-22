"""Tests de base — config, schémas Pydantic, sécurité JWT."""
import pytest
from app.core.config import get_settings
from app.models.schemas import QueryRequest, StreamChunk, SourceDoc, FeedbackRequest
from app.core.security import create_access_token, decode_token


def test_settings_defaults():
    s = get_settings()
    assert s.embedding_dimensions == 384
    assert s.retrieval_top_k == 20
    assert s.rerank_top_n == 5
    assert s.chunk_size == 512
    assert s.chunk_overlap == 64


def test_query_request_validation():
    req = QueryRequest(question="Quelle est la politique de congés ?")
    assert req.collection == "general"
    assert req.stream is True


def test_query_request_too_short():
    with pytest.raises(Exception):
        QueryRequest(question="")


def test_query_request_too_long():
    with pytest.raises(Exception):
        QueryRequest(question="x" * 2001)


def test_stream_chunk_with_log_id():
    chunk = StreamChunk(type="done", query_log_id="abc-123")
    assert chunk.query_log_id == "abc-123"
    assert chunk.content is None


def test_feedback_request_bounds():
    FeedbackRequest(query_log_id="uuid", feedback=1)
    FeedbackRequest(query_log_id="uuid", feedback=-1)
    with pytest.raises(Exception):
        FeedbackRequest(query_log_id="uuid", feedback=2)


def test_source_doc_schema():
    src = SourceDoc(
        id="abc",
        title="Test doc",
        source_type="pdf",
        source_id="uploads/test.pdf",
        content_excerpt="Extrait de texte",
        score=0.85,
    )
    assert src.url is None
    assert src.score == 0.85


def test_jwt_roundtrip():
    token = create_access_token("user-42")
    user_id = decode_token(token)
    assert user_id == "user-42"


def test_jwt_invalid_token():
    assert decode_token("not.a.valid.token") is None
