"""Tests des endpoints API — auth, query, feedback, ingest."""
from __future__ import annotations

import io
import uuid

import pytest
from httpx import AsyncClient

# Préfixe unique par run de test — évite les conflits d'email en DB
_RUN = uuid.uuid4().hex[:8]


def _email(tag: str) -> str:
    return f"ci_{_RUN}_{tag}@test.example"


# ── Auth ─────────────────────────────────────────────────────────────────────

async def test_health(client: AsyncClient):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_register(client: AsyncClient):
    r = await client.post("/api/auth/register", json={"email": _email("reg"), "password": "pass1234"})
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == _email("reg")
    assert data["role"] == "user"
    assert data["allowed_collections"] == ["general"]
    assert "id" in data


async def test_register_duplicate(client: AsyncClient):
    email = _email("dup")
    await client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
    r = await client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
    assert r.status_code == 409


async def test_login_success(client: AsyncClient):
    email = _email("login")
    await client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
    r = await client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
    assert r.status_code == 200
    tokens = r.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient):
    email = _email("wp")
    await client.post("/api/auth/register", json={"email": email, "password": "correct"})
    r = await client.post("/api/auth/login", json={"email": email, "password": "wrong"})
    assert r.status_code == 401


async def test_login_unknown_email(client: AsyncClient):
    r = await client.post("/api/auth/login", json={"email": "nobody@nowhere.com", "password": "x"})
    assert r.status_code == 401


async def test_me_authenticated(client: AsyncClient):
    email = _email("me")
    await client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
    r = await client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
    token = r.json()["access_token"]
    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == email


async def test_me_unauthenticated(client: AsyncClient):
    r = await client.get("/api/auth/me")
    assert r.status_code == 401


async def test_token_refresh(client: AsyncClient):
    email = _email("refresh")
    await client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
    r = await client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
    refresh = r.json()["refresh_token"]
    r = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200
    assert "access_token" in r.json()


async def test_refresh_with_access_token_rejected(client: AsyncClient):
    email = _email("badrefresh")
    await client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
    r = await client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
    access = r.json()["access_token"]
    r = await client.post("/api/auth/refresh", json={"refresh_token": access})
    assert r.status_code == 401


# ── Query ─────────────────────────────────────────────────────────────────────

async def test_query_guest_general(client: AsyncClient, mock_hyde):
    r = await client.post("/api/query", json={
        "question": "Question de test pour la validation CI du pipeline RAG",
        "collection": "general",
        "stream": False,
    })
    assert r.status_code == 200
    data = r.json()
    assert "answer" in data
    assert "sources" in data
    assert isinstance(data["sources"], list)


async def test_query_guest_forbidden_collection(client: AsyncClient):
    r = await client.post("/api/query", json={
        "question": "Question de test pour la collection RH",
        "collection": "rh",
        "stream": False,
    })
    assert r.status_code == 403


async def test_query_too_short(client: AsyncClient):
    r = await client.post("/api/query", json={"question": "", "collection": "general"})
    assert r.status_code == 422


async def test_query_too_long(client: AsyncClient):
    r = await client.post("/api/query", json={"question": "x" * 2001, "collection": "general"})
    assert r.status_code == 422


async def test_query_authenticated_accesses_own_collection(client: AsyncClient, mock_hyde):
    email = _email("qauth")
    await client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
    r = await client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
    token = r.json()["access_token"]
    # User has allowed_collections=["general"] by default
    r = await client.post(
        "/api/query",
        json={"question": "Question de test authentifié pour le pipeline RAG", "collection": "general", "stream": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200


async def test_query_authenticated_forbidden_other_collection(client: AsyncClient):
    email = _email("qforbid")
    await client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
    r = await client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
    token = r.json()["access_token"]
    r = await client.post(
        "/api/query",
        json={"question": "Question test collection interdite pour cet utilisateur", "collection": "tech", "stream": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


# ── Feedback ──────────────────────────────────────────────────────────────────

async def test_feedback_invalid_uuid(client: AsyncClient):
    r = await client.post("/api/query/feedback", json={"query_log_id": "not-a-uuid", "feedback": 1})
    assert r.status_code == 400


async def test_feedback_invalid_value(client: AsyncClient):
    r = await client.post("/api/query/feedback", json={"query_log_id": str(uuid.uuid4()), "feedback": 2})
    assert r.status_code == 422


async def test_feedback_valid(client: AsyncClient):
    r = await client.post("/api/query/feedback", json={"query_log_id": str(uuid.uuid4()), "feedback": 1})
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_feedback_thumbs_down(client: AsyncClient):
    r = await client.post("/api/query/feedback", json={"query_log_id": str(uuid.uuid4()), "feedback": -1})
    assert r.status_code == 200


# ── Ingest ────────────────────────────────────────────────────────────────────

async def test_ingest_pdf_requires_auth(client: AsyncClient):
    r = await client.post(
        "/api/ingest/pdf",
        files={"file": ("test.pdf", io.BytesIO(b"%PDF-1.4 fake content"), "application/pdf")},
        data={"collection": "general"},
    )
    assert r.status_code == 401


async def test_ingest_pdf_requires_admin(client: AsyncClient):
    email = _email("inguser")
    await client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
    r = await client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
    token = r.json()["access_token"]
    r = await client.post(
        "/api/ingest/pdf",
        files={"file": ("test.pdf", io.BytesIO(b"%PDF-1.4 fake content"), "application/pdf")},
        data={"collection": "general"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403
