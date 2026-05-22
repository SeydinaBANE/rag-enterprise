"""HyDE — Hypothetical Document Embeddings (Gao et al., 2022).

Instead of embedding the raw question, ask the LLM to generate a short
hypothetical answer document, then embed that. Closes the vocabulary gap
between terse queries and dense document prose.

Enabled via HYDE_ENABLED=true in .env. Adds ~1 LLM call per query.
Falls back to raw query embedding on any error.
"""
from __future__ import annotations

import logging

from app.core.config import get_settings
from app.ingestion.embedder import embed_query
from app.rag.generator import _get_client

logger = logging.getLogger(__name__)
settings = get_settings()

_PROMPT = (
    "Génère un court extrait de document d'entreprise (2-3 phrases) qui répondrait "
    "directement à cette question. Écris uniquement le contenu du document, sans introduction.\n\n"
    "Question : {question}\n\nExtrait :"
)


async def hyde_embed(question: str) -> list[float]:
    try:
        client = _get_client()
        resp = await client.chat.completions.create(
            model=settings.llm_model,
            max_tokens=150,
            stream=False,
            messages=[{"role": "user", "content": _PROMPT.format(question=question)}],
        )
        hypothetical = resp.choices[0].message.content or question
        logger.debug("HyDE doc (%.80s...)", hypothetical)
        return await embed_query(hypothetical)
    except Exception as exc:
        logger.warning("HyDE failed (%s) — falling back to raw query embedding", exc)
        return await embed_query(question)
