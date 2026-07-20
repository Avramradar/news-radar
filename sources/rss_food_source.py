from __future__ import annotations

import hashlib
import html
import re
from pathlib import Path

import feedparser

from .base_source import BaseSource
from .food_source import FoodPost


class RssFoodSource(BaseSource):
    """Получает публикации из кулинарных RSS-лент."""

    SOURCE_FILE = Path("food_sources.txt")

    def fetch(self) -> list[FoodPost]:
        if not self.SOURCE_FILE.exists():
            print("Файл food_sources.txt не найден.")
            return []

        urls_text = self.SOURCE_FILE.read_text(
            encoding="utf-8"
        ).strip()

        if not urls_text:
            return []

        feed_urls = [
            line.strip()
            for line in urls_text.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

        posts: list[FoodPost] = []

        for feed_url in feed_urls:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:2]:
                title = str(entry.get("title", "")).strip()
                source_url = str(entry.get("link", "")).strip()

                if not title or not source_url:
                    continue

                raw_summary = str(
                    entry.get(
                        "summary",
                        entry.get("description", ""),
                    )
                )

                summary = self._clean_html(raw_summary)
                image_url = self._extract_image(entry)
                message_id = self._make_message_id(source_url)

                text = title

                if summary:
                    text += f"\n\n{summary}"

                posts.append(
                    FoodPost(
                        text=text,
                        message_id=message_id,
                        source_url=source_url,
                        image_url=image_url,
                    )
                )

        return posts
    @staticmethod
    def _clean_html(value: str) -> str:
        clean = re.sub(r"<[^>]+>", " ", value)
        clean = html.unescape(clean)
        clean = re.sub(r"\s+", " ", clean)
        return clean.strip()

    @staticmethod
    def _make_message_id(source_url: str) -> int:
        digest = hashlib.sha256(
            source_url.encode("utf-8")
        ).hexdigest()

        return int(digest[:12], 16)
    @staticmethod
    def _extract_image(entry) -> str:
        media_content = entry.get("media_content", [])

        if media_content:
            image_url = media_content[0].get("url", "")
            if image_url:
                return str(image_url)

        media_thumbnail = entry.get("media_thumbnail", [])

        if media_thumbnail:
            image_url = media_thumbnail[0].get("url", "")
            if image_url:
                return str(image_url)

        enclosures = entry.get("enclosures", [])

        for enclosure in enclosures:
            enclosure_type = str(enclosure.get("type", ""))

            if enclosure_type.startswith("image/"):
                return str(enclosure.get("href", ""))

        raw_summary = str(
            entry.get(
                "summary",
                entry.get("description", ""),
            )
        )

        match = re.search(
            r'<img[^>]+src=["\']([^"\']+)["\']',
            raw_summary,
            flags=re.IGNORECASE,
        )

        if match:
            return html.unescape(match.group(1))

        return ""
