from __future__ import annotations

import hashlib
import html
import re
from pathlib import Path

import feedparser
import requests

from food_models import FoodPost
from sources.base_source import BaseSource


class YouTubeSource(BaseSource):
    """
    Получает последние видео кулинарных YouTube-каналов.

    Источники читаются из food_sources.txt:
    youtube:@ChannelHandle
    """

    SOURCE_FILE = Path("food_sources.txt")
    VIDEOS_PER_CHANNEL = 2
    TIMEOUT = 20

    def fetch(self) -> list[FoodPost]:
        handles = self._load_handles()

        if not handles:
            print("YouTube-источники не найдены.")
            return []

        posts: list[FoodPost] = []

        for handle in handles:
            try:
                channel_id = self._resolve_channel_id(
                    handle
                )

                if not channel_id:
                    print(
                        "YouTube: не найден channel_id: "
                        f"@{handle}"
                    )
                    continue

                channel_posts = self._fetch_feed(
                    handle=handle,
                    channel_id=channel_id,
                )

                posts.extend(channel_posts)

                print(
                    f"YouTube OK: @{handle}; "
                    f"получено публикаций: "
                    f"{len(channel_posts)}"
                )
            except Exception as error:
                print(
                    f"YouTube ERROR: @{handle}: {error}"
                )

        print(
            "YouTube-обработка завершена. "
            f"Получено публикаций: {len(posts)}"
        )

        return posts

    def _load_handles(self) -> list[str]:
        if not self.SOURCE_FILE.exists():
            print("Файл food_sources.txt не найден.")
            return []

        handles: list[str] = []

        for raw_line in self.SOURCE_FILE.read_text(
            encoding="utf-8"
        ).splitlines():
            line = raw_line.strip()

            if not line or line.startswith("#"):
                continue

            if not line.lower().startswith("youtube:"):
                continue

            handle = line.split(":", 1)[1].strip()
            handle = handle.removeprefix("@").strip()

            if handle:
                handles.append(handle)

        return list(dict.fromkeys(handles))

    def _resolve_channel_id(
        self,
        handle: str,
    ) -> str:
        channel_url = (
            "https://www.youtube.com/"
            f"@{handle}"
        )

        response = requests.get(
            channel_url,
            timeout=self.TIMEOUT,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Linux; Android 13) "
                    "AppleWebKit/537.36 "
                    "Chrome/120.0 Safari/537.36"
                )
            },
        )

        response.raise_for_status()

        patterns = (
            r'"channelId":"(UC[^"]+)"',
            r'"externalId":"(UC[^"]+)"',
            r'<meta itemprop="channelId" content="([^"]+)"',
        )

        for pattern in patterns:
            match = re.search(
                pattern,
                response.text,
            )

            if match:
                return match.group(1)

        return ""

    def _fetch_feed(
        self,
        handle: str,
        channel_id: str,
    ) -> list[FoodPost]:
        feed_url = (
            "https://www.youtube.com/feeds/videos.xml"
            f"?channel_id={channel_id}"
        )

        feed = feedparser.parse(feed_url)

        if getattr(feed, "bozo", False):
            error = getattr(
                feed,
                "bozo_exception",
                "",
            )

            print(
                f"YouTube RSS warning @{handle}: "
                f"{error}"
            )

        entries = getattr(
            feed,
            "entries",
            [],
        )

        posts: list[FoodPost] = []

        for entry in entries[: self.VIDEOS_PER_CHANNEL]:
            title = str(
                entry.get("title", "")
            ).strip()

            source_url = str(
                entry.get("link", "")
            ).strip()

            if not title or not source_url:
                continue

            description = self._extract_description(
                entry
            )

            text = title

            if description:
                text += f"\n\n{description}"

            image_url = self._extract_image(entry)
            message_id = self._make_message_id(
                source_url
            )

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
    def _extract_description(entry) -> str:
        media_group = entry.get(
            "media_group",
            {},
        )

        description = str(
            media_group.get(
                "media_description",
                entry.get(
                    "summary",
                    entry.get("description", ""),
                ),
            )
        )

        description = re.sub(
            r"<[^>]+>",
            " ",
            description,
        )

        description = html.unescape(description)

        description = re.sub(
            r"[ \t]+",
            " ",
            description,
        )

        description = re.sub(
            r"\n{3,}",
            "\n\n",
            description,
        )

        return description.strip()

    @staticmethod
    def _extract_image(entry) -> str:
        media_group = entry.get(
            "media_group",
            {},
        )

        thumbnails = media_group.get(
            "media_thumbnail",
            [],
        )

        if thumbnails:
            return str(
                thumbnails[-1].get("url", "")
            ).strip()

        media_thumbnail = entry.get(
            "media_thumbnail",
            [],
        )

        if media_thumbnail:
            return str(
                media_thumbnail[-1].get("url", "")
            ).strip()

        return ""

    @staticmethod
    def _make_message_id(source_url: str) -> int:
        digest = hashlib.sha256(
            source_url.encode("utf-8")
        ).hexdigest()

        return int(digest[:12], 16)
