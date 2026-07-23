from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs

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
    TIMEOUT = 25

    USER_AGENT = (
    "Mozilla/5.0 "
    "(Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

    def __init__(self) -> None:
        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": self.USER_AGENT,
                "Accept-Language": (
                    "ru-RU,ru;q=0.9,en;q=0.6"
                ),
            }
        )

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
                    f"YouTube ERROR: @{handle}: "
                    f"{type(error).__name__}: {error}"
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

            if not line.lower().startswith(
                "youtube:"
            ):
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

        response = self.session.get(
            channel_url,
            timeout=self.TIMEOUT,
        )

        response.raise_for_status()

        patterns = (
            r'"channelId":"(UC[^"]+)"',
            r'"externalId":"(UC[^"]+)"',
            (
                r'<meta\s+itemprop="channelId"\s+'
                r'content="([^"]+)"'
            ),
            (
                r'<link\s+rel="canonical"\s+'
                r'href="https://www\.youtube\.com/'
                r'channel/(UC[^"]+)"'
            ),
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
            "https://www.youtube.com/"
            "feeds/videos.xml"
            f"?channel_id={channel_id}"
        )

        response = self.session.get(
            feed_url,
            timeout=self.TIMEOUT,
        )

        response.raise_for_status()

        feed = feedparser.parse(
            response.content
        )

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

        for entry in entries[
            : self.VIDEOS_PER_CHANNEL
        ]:
            try:
                post = self._entry_to_post(
                    handle=handle,
                    entry=entry,
                )

                if post is not None:
                    posts.append(post)

            except Exception as error:
                print(
                    f"YouTube video ERROR @{handle}: "
                    f"{type(error).__name__}: {error}"
                )

        return posts

    def _entry_to_post(
        self,
        handle: str,
        entry,
    ) -> FoodPost | None:
        title = self._clean_text(
            str(entry.get("title", ""))
        )

        source_url = str(
            entry.get("link", "")
        ).strip()

        if not title or not source_url:
            return None

        rss_description = (
            self._extract_rss_description(entry)
        )

        page_description = (
            self._fetch_full_description(
                source_url
            )
        )

        description = (
            self._choose_best_description(
                rss_description,
                page_description,
            )
        )

        text_parts = [title]

        if description:
            text_parts.append(description)

        text = "\n\n".join(text_parts).strip()

        image_url = self._extract_image(
            entry
        )

        if not image_url:
            image_url = (
                self._make_thumbnail_url(
                    source_url
                )
            )

        message_id = self._make_message_id(
            source_url
        )

        print(
            f"YouTube video @{handle}: "
            f"title={len(title)}, "
            f"rss_description="
            f"{len(rss_description)}, "
            f"full_description="
            f"{len(page_description)}, "
            f"result={len(description)}"
        )

        return FoodPost(
            text=text,
            message_id=message_id,
            source_url=source_url,
            image_url=image_url,
        )

    def _fetch_full_description(
        self,
        source_url: str,
    ) -> str:
        """
        Получает полное описание непосредственно
        со страницы видео.

        Это запасной способ на случай, если RSS
        вернул сокращённое описание.
        """
        try:
            response = self.session.get(
                source_url,
                timeout=self.TIMEOUT,
            )

            response.raise_for_status()

        except requests.RequestException as error:
            print(
                "YouTube description request "
                f"failed: {error}"
            )
            return ""

        page_text = response.text

        description = (
            self._extract_short_description(
                page_text
            )
        )

        if description:
            return self._clean_text(description)

        description = (
            self._extract_meta_description(
                page_text
            )
        )

        return self._clean_text(description)

    @staticmethod
    def _extract_short_description(
        page_text: str,
    ) -> str:
        """
        Ищет shortDescription в JSON страницы.

        Значение содержит экранированные переводы
        строк и Unicode-последовательности.
        """
        pattern = (
            r'"shortDescription":'
            r'"((?:\\.|[^"\\])*)"'
        )

        match = re.search(
            pattern,
            page_text,
        )

        if not match:
            return ""

        encoded_value = match.group(1)

        try:
            return json.loads(
                f'"{encoded_value}"'
            )
        except json.JSONDecodeError:
            return (
                encoded_value
                .replace(r"\n", "\n")
                .replace(r"\"", '"')
                .replace(r"\\", "\\")
            )

    @staticmethod
    def _extract_meta_description(
        page_text: str,
    ) -> str:
        patterns = (
            (
                r'<meta\s+name="description"\s+'
                r'content="([^"]*)"'
            ),
            (
                r'<meta\s+property="og:description"\s+'
                r'content="([^"]*)"'
            ),
        )

        for pattern in patterns:
            match = re.search(
                pattern,
                page_text,
                flags=re.IGNORECASE,
            )

            if match:
                return html.unescape(
                    match.group(1)
                )

        return ""

    @classmethod
    def _extract_rss_description(
        cls,
        entry,
    ) -> str:
        media_group = entry.get(
            "media_group",
            {},
        )

        description = str(
            media_group.get(
                "media_description",
                entry.get(
                    "summary",
                    entry.get(
                        "description",
                        "",
                    ),
                ),
            )
        )

        return cls._clean_text(description)

    @staticmethod
    def _choose_best_description(
        rss_description: str,
        page_description: str,
    ) -> str:
        """
        Выбирает наиболее полное описание.

        Обычно описание со страницы видео длиннее,
        но иногда RSS содержит более полезный текст.
        """
        candidates = [
            value.strip()
            for value in (
                rss_description,
                page_description,
            )
            if value and value.strip()
        ]

        if not candidates:
            return ""

        return max(
            candidates,
            key=len,
        )

    @staticmethod
    def _clean_text(text: str) -> str:
        if not text:
            return ""

        text = re.sub(
            r"<br\s*/?>",
            "\n",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"</p\s*>",
            "\n",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"<[^>]+>",
            " ",
            text,
        )

        text = html.unescape(text)

        text = text.replace(
            "\r\n",
            "\n",
        )

        text = text.replace(
            "\r",
            "\n",
        )

        # Удаляем лишние пробелы,
        # но сохраняем переносы строк.
        lines: list[str] = []

        for raw_line in text.splitlines():
            line = re.sub(
                r"[ \t]+",
                " ",
                raw_line,
            ).strip()

            lines.append(line)

        text = "\n".join(lines)

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text,
        )

        return text.strip()

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
                thumbnails[-1].get(
                    "url",
                    "",
                )
            ).strip()

        media_thumbnail = entry.get(
            "media_thumbnail",
            [],
        )

        if media_thumbnail:
            return str(
                media_thumbnail[-1].get(
                    "url",
                    "",
                )
            ).strip()

        return ""

    @staticmethod
    def _make_thumbnail_url(
        source_url: str,
    ) -> str:
        video_id = (
            YouTubeSource._extract_video_id(
                source_url
            )
        )

        if not video_id:
            return ""

        return (
            "https://i.ytimg.com/vi/"
            f"{video_id}/hqdefault.jpg"
        )

    @staticmethod
    def _extract_video_id(
        source_url: str,
    ) -> str:
        parsed = urlparse(source_url)

        if parsed.hostname in {
            "youtu.be",
            "www.youtu.be",
        }:
            return parsed.path.strip("/")

        if parsed.path == "/watch":
            query = parse_qs(
                parsed.query
            )

            return query.get(
                "v",
                [""],
            )[0]

        match = re.search(
            r"/(?:shorts|embed)/([^/?#]+)",
            parsed.path,
        )

        if match:
            return match.group(1)

        return ""

    @staticmethod
    def _make_message_id(
        source_url: str,
    ) -> int:
        digest = hashlib.sha256(
            source_url.encode("utf-8")
        ).hexdigest()

        return int(
            digest[:12],
            16,
        )
