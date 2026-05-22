"""Fixtures partagées pour tous les tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.main import app

settings = get_settings()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Remplace le moteur SQLAlchemy par NullPool pour les tests.

    NullPool crée une connexion par requête — évite les conflits asyncpg
    (InterfaceError: cannot perform operation: another operation is in progress).
    """
    from app.core import database

    test_engine = create_async_engine(settings.database_url, poolclass=NullPool)
    database.engine = test_engine
    database.AsyncSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)

    yield

    await test_engine.dispose()


@pytest.fixture(scope="session")
async def client(setup_test_db) -> AsyncClient:
    """Client HTTP partagé sur toute la session."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def mock_hyde():
    """Remplace _get_query_embedding par un vecteur nul — évite fastembed + LLM en CI."""
    with patch("app.rag.pipeline._get_query_embedding", new_callable=AsyncMock) as m:
        m.return_value = [0.0] * 384
        yield m
