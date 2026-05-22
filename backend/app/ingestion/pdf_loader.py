from __future__ import annotations
import logging
from pathlib import Path
import pdfplumber
from app.ingestion.base import BaseLoader

logger = logging.getLogger(__name__)


class PDFLoader(BaseLoader):
    source_type = "pdf"

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)

    def _source_id(self) -> str:
        return str(self.file_path)

    async def load(self) -> list[tuple[str, dict]]:
        results: list[tuple[str, dict]] = []
        title = self.file_path.stem

        with pdfplumber.open(self.file_path) as pdf:
            full_text_parts: list[str] = []

            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""

                # Extract tables as markdown-style text
                for table in page.extract_tables():
                    if table:
                        table_text = _table_to_text(table)
                        text += f"\n\n{table_text}\n"

                if text.strip():
                    full_text_parts.append(text)

            full_text = "\n\n".join(full_text_parts)
            if full_text.strip():
                results.append((
                    full_text,
                    {
                        "source_id": str(self.file_path),
                        "title": title,
                        "source_type": "pdf",
                        "total_pages": len(pdf.pages),
                    },
                ))

        logger.info("PDF loaded: %s (%d chars)", self.file_path.name, len(full_text) if results else 0)
        return results


def _table_to_text(table: list[list[str | None]]) -> str:
    rows = []
    for row in table:
        cells = [str(cell or "").strip() for cell in row]
        rows.append(" | ".join(cells))
    return "\n".join(rows)
