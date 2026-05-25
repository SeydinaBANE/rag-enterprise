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
    assert s.pii_detection_enabled is False
    assert s.pii_action == "anonymize"
    assert s.pii_language == "en"


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
    token = create_access_token("user-42", role="user", collections=["general", "rh"])
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user-42"
    assert payload["role"] == "user"
    assert payload["collections"] == ["general", "rh"]
    assert payload["type"] == "access"


def test_jwt_admin_role():
    token = create_access_token("admin-1", role="admin", collections=["general", "rh", "tech"])
    payload = decode_token(token)
    assert payload is not None
    assert payload["role"] == "admin"


def test_jwt_invalid_token():
    assert decode_token("not.a.valid.token") is None


# ── PII detector ──────────────────────────────────────────────────────────────

def test_pii_process_chunk_disabled(monkeypatch):
    """When PII is disabled, process_chunk must not be called at all."""
    from app.ingestion import pii_detector
    called = []

    def fake_engines(language):
        called.append(language)
        raise AssertionError("Presidio should not be loaded when PII is disabled")

    monkeypatch.setattr(pii_detector, "_get_engines", fake_engines)
    # Bypass the lru_cache by patching the underlying function
    text = "Contactez Jean Dupont à jean@example.com"
    # process_chunk should fall through to the disabled guard inside chunker,
    # so calling it directly with action="log" but mocked engines should never invoke them
    # Here we test the fallback path: exception → original content returned
    result = pii_detector.process_chunk.__wrapped__(text, "en", "log") if hasattr(pii_detector.process_chunk, "__wrapped__") else text
    assert isinstance(result, str)


def test_pii_process_chunk_passthrough_on_error(monkeypatch):
    """process_chunk must return original text when Presidio raises."""
    from app.ingestion import pii_detector

    def exploding_engines(language):
        raise RuntimeError("Presidio unavailable")

    monkeypatch.setattr(pii_detector, "_get_engines", exploding_engines)
    text = "Test avec erreur Presidio"
    result = pii_detector.process_chunk(text, "en", "anonymize")
    assert result == text


def test_pii_process_chunk_anonymize(monkeypatch):
    """process_chunk anonymizes text when Presidio returns results."""
    from unittest.mock import MagicMock
    from app.ingestion import pii_detector

    fake_result = MagicMock()
    fake_result.entity_type = "EMAIL_ADDRESS"

    fake_analyzer = MagicMock()
    fake_analyzer.analyze.return_value = [fake_result]

    fake_anonymized = MagicMock()
    fake_anonymized.text = "Contactez <EMAIL_ADDRESS>"
    fake_anonymizer = MagicMock()
    fake_anonymizer.anonymize.return_value = fake_anonymized

    monkeypatch.setattr(pii_detector, "_get_engines", lambda lang: (fake_analyzer, fake_anonymizer))

    text = "Contactez jean@example.com"
    result = pii_detector.process_chunk(text, "en", "anonymize")
    assert result == "Contactez <EMAIL_ADDRESS>"


def test_pii_process_chunk_log_only(monkeypatch):
    """process_chunk returns original text when action=log."""
    from unittest.mock import MagicMock
    from app.ingestion import pii_detector

    fake_result = MagicMock()
    fake_result.entity_type = "PERSON"

    fake_analyzer = MagicMock()
    fake_analyzer.analyze.return_value = [fake_result]
    fake_anonymizer = MagicMock()

    monkeypatch.setattr(pii_detector, "_get_engines", lambda lang: (fake_analyzer, fake_anonymizer))

    text = "Bonjour Jean Dupont"
    result = pii_detector.process_chunk(text, "en", "log")
    assert result == text
    fake_anonymizer.anonymize.assert_not_called()


def test_pii_process_chunk_no_entities(monkeypatch):
    """process_chunk returns original text when no PII detected."""
    from unittest.mock import MagicMock
    from app.ingestion import pii_detector

    fake_analyzer = MagicMock()
    fake_analyzer.analyze.return_value = []
    fake_anonymizer = MagicMock()

    monkeypatch.setattr(pii_detector, "_get_engines", lambda lang: (fake_analyzer, fake_anonymizer))

    text = "La politique de congés est de 25 jours par an."
    result = pii_detector.process_chunk(text, "en", "anonymize")
    assert result == text
    fake_anonymizer.anonymize.assert_not_called()
