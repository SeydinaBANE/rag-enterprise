from __future__ import annotations

import logging

from atlassian import Confluence
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.ingestion.base import BaseLoader

logger = logging.getLogger(__name__)
settings = get_settings()


class ConfluenceLoader(BaseLoader):
    source_type = "confluence"

    def __init__(self, space_key: str):
        self.space_key = space_key
        self._client = Confluence(
            url=settings.confluence_url,
            username=settings.confluence_username,
            password=settings.confluence_api_token,
            cloud=True,
        )

    def _source_id(self) -> str:
        return f"confluence:{self.space_key}"

    async def load(self) -> list[tuple[str, dict]]:
        results: list[tuple[str, dict]] = []
        start = 0
        limit = 50

        while True:
            pages = self._client.get_all_pages_from_space(
                self.space_key, start=start, limit=limit, expand="body.storage,version"
            )
            if not pages:
                break

            for page in pages:
                html = page.get("body", {}).get("storage", {}).get("value", "")
                text = _html_to_text(html)
                if not text.strip():
                    continue

                page_id = page.get("id", "")
                title = page.get("title", "")
                url = f"{settings.confluence_url}/wiki/spaces/{self.space_key}/pages/{page_id}"

                results.append((
                    text,
                    {
                        "source_id": url,
                        "title": title,
                        "source_type": "confluence",
                        "space_key": self.space_key,
                        "page_id": page_id,
                        "url": url,
                    },
                ))

            start += limit
            if len(pages) < limit:
                break

        logger.info("Confluence loaded: %d pages from space %s", len(results), self.space_key)
        return results


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # Remove navigation and macro panels
    for tag in soup.find_all(["ac:structured-macro", "ac:parameter"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)
