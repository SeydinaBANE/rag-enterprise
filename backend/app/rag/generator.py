from __future__ import annotations
import logging
from typing import AsyncIterator
from openai import AsyncOpenAI
from app.models.schemas import SourceDoc
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client: AsyncOpenAI | None = None

SYSTEM_PROMPT = """Tu es un assistant interne d'entreprise. Tu réponds aux questions des employés en te basant UNIQUEMENT sur les documents fournis dans le contexte.

Règles :
- Réponds toujours en français
- Cite tes sources avec [1], [2], etc.
- Si la réponse n'est pas dans les documents, dis-le clairement : "Je n'ai pas trouvé d'information sur ce sujet dans les documents disponibles."
- Ne fabrique jamais d'information
- Sois concis et précis
- Si plusieurs documents se contredisent, mentionne la contradiction"""


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            default_headers={
                "HTTP-Referer": settings.openrouter_site_url,
                "X-Title": settings.openrouter_site_name,
            },
        )
    return _client


def _build_context(sources: list[SourceDoc]) -> str:
    parts = []
    for i, src in enumerate(sources, start=1):
        title = src.title or src.source_id
        parts.append(f"[{i}] **{title}** ({src.source_type})\n{src.content_excerpt}")
    return "\n\n---\n\n".join(parts)


async def generate_stream(question: str, sources: list[SourceDoc]) -> AsyncIterator[str]:
    """Stream answer tokens via OpenRouter."""
    client = _get_client()
    context = _build_context(sources)

    stream = await client.chat.completions.create(
        model=settings.llm_model,
        max_tokens=2048,
        stream=True,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Documents disponibles :\n\n{context}\n\n---\n\nQuestion : {question}",
            },
        ],
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


async def generate(question: str, sources: list[SourceDoc]) -> tuple[str, int | None]:
    """Non-streaming generation. Returns (answer, tokens_used)."""
    client = _get_client()
    context = _build_context(sources)

    response = await client.chat.completions.create(
        model=settings.llm_model,
        max_tokens=2048,
        stream=False,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Documents disponibles :\n\n{context}\n\n---\n\nQuestion : {question}",
            },
        ],
    )
    answer = response.choices[0].message.content or ""
    tokens = response.usage.total_tokens if response.usage else None
    return answer, tokens
