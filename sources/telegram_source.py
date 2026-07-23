from __future__ import annotations

import hashlib
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from food_models import FoodPost
from sources.base_source import BaseSource


class TelegramSource(BaseSource):
    """
    Получает свежие публикации из публичных Telegram-каналов.

    Источники читаются из food_sources.txt:
    telegram:@channel_name
    """

    SOURCE_FILE = Path("food_sources.txt")
    POSTS_PER_CHANNEL = 3
    TIMEOUT = 20

    def fetch(self) -> list[FoodPost]:
        channels = self._load_channels()

        if not channels:
            print("Telegram-источники не найдены.")
            return []

        posts: list[FoodPost] = []

        for channel in channels:
            try:
                channel_posts = self._fetch_channel(channel)
                posts.extend(channel_posts)

                print(
                    f"Telegram OK: @{channel}; "
                    f"получено публикаций: {len(channel_posts)}"
                )
            except Exception as error:
                print(
                    f"Telegram ERROR: @{channel}: {error}"
                )

        print(
            "Telegram-обработка завершена. "
            f"Получено публикаций: {len(posts)}"
        )

        return posts

    def _load_channels(self) -> list[str]:
        if not self.SOURCE_FILE.exists():
            print("Файл food_sources.txt не найден.")
            return []

        channels: list[str] = []

        for raw_line in self.SOURCE_FILE.read_text(
            encoding="utf-8"
        ).splitlines():
            line = raw_line.strip()

            if not line or line.startswith("#"):
                continue

            if not line.lower().startswith("telegram:"):
                continue

            channel = line.split(":", 1)[1].strip()
            channel = channel.removeprefix("@").strip()

            if channel:
                channels.append(channel)

        return list(dict.fromkeys(channels))

    def _fetch_channel(
        self,
        channel: str,
    ) -> list[FoodPost]:
        url = f"https://t.me/s/{channel}"

        response = requests.get(
            url,
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

        soup = BeautifulSoup(
            response.text,
            "lxml",
        )

        message_nodes = soup.select(
            ".tgme_widget_message_wrap"
        )

        posts: list[FoodPost] = []

        for node in message_nodes[-self.POSTS_PER_CHANNEL:]:
            message = node.select_one(
                ".tgme_widget_message"
            )

            text_node = node.select_one(
                ".tgme_widget_message_text"
            )

            if message is None or text_node is None:
                continue

            text = text_node.get_text(
                "\n",
                strip=True,
            )

            if not text:
                continue

            data_post = str(
                message.get("data-post", "")
            ).strip()

            if not data_post:
                continue

            source_url = f"https://t.me/{data_post}"
            message_id = self._make_message_id(source_url)
            image_url = self._extract_image(node)

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
    def _extract_image(node) -> str:
        photo = node.select_one(
            ".tgme_widget_message_photo_wrap"
        )

        if photo is not None:
            style = str(
                photo.get("style", "")
            )

            match = re.search(
                r"background-image:url\(['\"]?([^'\")]+)",
                style,
            )

            if match:
                return match.group(1)

        image = node.select_one("img")

        if image is not None:
            return str(
                image.get("src", "")
            ).strip()

        return ""

    @staticmethod
    def _make_message_id(source_url: str) -> int:
        digest = hashlib.sha256(
            source_url.encode("utf-8")
        ).hexdigest()

        return int(digest[:12], 16)
