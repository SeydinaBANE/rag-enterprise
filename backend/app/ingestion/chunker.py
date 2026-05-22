from __future__ import annotations

import re
from dataclasses import dataclass

from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.core.config import get_settings

settings = get_settings()


@dataclass
class Chunk:
    content: str
    metadata: dict


def chunk_text(text: str, metadata: dict | None = None) -> list[Chunk]:
    """Hybrid chunking: section-aware then recursive character split."""
    metadata = metadata or {}
    sections = _split_by_headings(text)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[Chunk] = []
    for section_title, section_text in sections:
        sub_chunks = splitter.split_text(section_text)
        for i, content in enumerate(sub_chunks):
            content = content.strip()
            if len(content) < 50:
                continue
            chunk_meta = {**metadata, "section": section_title, "chunk_index": i}
            chunks.append(Chunk(content=content, metadata=chunk_meta))

    return chunks


def _split_by_headings(text: str) -> list[tuple[str, str]]:
    """Split markdown/structured text by H1/H2 headings."""
    heading_pattern = re.compile(r"^(#{1,2})\s+(.+)$", re.MULTILINE)
    matches = list(heading_pattern.finditer(text))

    if not matches:
        return [("", text)]

    sections: list[tuple[str, str]] = []
    prev_end = 0
    prev_title = ""

    for match in matches:
        if match.start() > prev_end:
            sections.append((prev_title, text[prev_end : match.start()]))
        prev_title = match.group(2).strip()
        prev_end = match.end()

    sections.append((prev_title, text[prev_end:]))
    return [(t, c) for t, c in sections if c.strip()]
