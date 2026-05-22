from __future__ import annotations

import json
import logging
from pathlib import Path

from app.core.config import get_settings
from app.ingestion.base import BaseLoader

logger = logging.getLogger(__name__)
settings = get_settings()


class SlackExportLoader(BaseLoader):
    """Load from a Slack export directory (zip extracted)."""
    source_type = "slack"

    def __init__(self, export_dir: str | Path):
        self.export_dir = Path(export_dir)

    def _source_id(self) -> str:
        return str(self.export_dir)

    async def load(self) -> list[tuple[str, dict]]:
        results: list[tuple[str, dict]] = []

        for channel_dir in self.export_dir.iterdir():
            if not channel_dir.is_dir():
                continue
            channel_name = channel_dir.name
            messages: list[str] = []

            for json_file in sorted(channel_dir.glob("*.json")):
                with open(json_file) as f:
                    day_messages = json.load(f)

                for msg in day_messages:
                    if msg.get("type") != "message" or msg.get("subtype"):
                        continue
                    text = msg.get("text", "").strip()
                    if len(text) < 20:
                        continue
                    messages.append(text)

            if messages:
                # Group messages into ~2000 char blocks
                blocks = _group_messages(messages, max_chars=2000)
                for i, block in enumerate(blocks):
                    results.append((
                        block,
                        {
                            "source_id": f"slack:{channel_name}:{i}",
                            "title": f"#{channel_name}",
                            "source_type": "slack",
                            "channel": channel_name,
                        },
                    ))

        logger.info("Slack loaded: %d blocks from %s", len(results), self.export_dir)
        return results


def _group_messages(messages: list[str], max_chars: int) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    current_len = 0

    for msg in messages:
        if current_len + len(msg) > max_chars and current:
            blocks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(msg)
        current_len += len(msg)

    if current:
        blocks.append("\n".join(current))
    return blocks
