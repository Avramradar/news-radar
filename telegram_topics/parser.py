"""Парсер публичных Telegram-каналов через страницы t.me/s/."""

from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag


@dataclass(frozen=True)
class TelegramPost:
    """Публикация, полученная из публичного Telegram-канала."""

    channel: str
    text: str
    message_id: int
    source_url: str
    image_url: str = ""


class TelegramPublicParser:
    """Читает свежие сообщения из публичных Telegram-каналов."""

    TIMEOUT = 20

    USER_AGENT = (
        "Mozilla/5.0 "
        "(Linux; Android 13) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )

    def __init__(self, posts_per_channel: int = 10) -> None:
        if posts_per_channel < 1:
            raise ValueError(
                "posts_per_channel должен быть больше нуля."
            )

        self.posts_per_channel = posts_per_channel

    def fetch_channel(self, channel: str) -> list[TelegramPost]:
        """ Получает последние публикации одного публичного канала. Канал можно передавать в форматах: channel_name @channel_name https://t.me/channel_name https://t.me/s/channel_name """
        normalized_channel = self.normalize_channel(channel)

        if not normalized_channel:
            raise ValueError(
                "Не указан username Telegram-канала."
            )

        url = f"https://t.me/s/{normalized_channel}"

        response = requests.get(
            url,
            timeout=self.TIMEOUT,
            headers={
                "User-Agent": self.USER_AGENT,
                "Accept-Language": "ru,en;q=0.8",
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

        posts: list[TelegramPost] = []

        for node in message_nodes[-self.posts_per_channel:]:
            post = self._parse_message(
                node=node,
                channel=normalized_channel,
            )

            if post is not None:
                posts.append(post)

        return posts

    def fetch_channels( self, channels: list[str], ) -> list[TelegramPost]:
        """Получает публикации из нескольких каналов."""
        posts: list[TelegramPost] = []

        for raw_channel in channels:
            channel = self.normalize_channel(raw_channel)

            if not channel:
                continue

            try:
                channel_posts = self.fetch_channel(channel)
                posts.extend(channel_posts)

                print(
                    f"Telegram parser OK: @{channel}; "
                    f"получено публикаций: {len(channel_posts)}"
                )
            except Exception as error:
                print(
                    f"Telegram parser ERROR: @{channel}: {error}"
                )

        return posts

    def _parse_message( self, node: Tag, channel: str, ) -> TelegramPost | None:
        """Разбирает один блок Telegram-сообщения."""
        message = node.select_one(
            ".tgme_widget_message"
        )

        text_node = node.select_one(
            ".tgme_widget_message_text"
        )

        if message is None or text_node is None:
            return None

        text = text_node.get_text(
            "\n",
            strip=True,
        )

        if not text:
            return None

        data_post = str(
            message.get("data-post", "")
        ).strip()

        if not data_post:
            return None

        source_url = f"https://t.me/{data_post}"

        return TelegramPost(
            channel=channel,
            text=text,
            message_id=self._make_message_id(source_url),
            source_url=source_url,
            image_url=self._extract_image(node),
        )

    @staticmethod
    def normalize_channel(channel: str) -> str:
        """Приводит ссылку или username канала к чистому username."""
        normalized = channel.strip()

        normalized = re.sub(
            r"^https?://",
            "",
            normalized,
            flags=re.IGNORECASE,
        )

        normalized = re.sub(
            r"^(www\.)?t\.me/",
            "",
            normalized,
            flags=re.IGNORECASE,
        )

        normalized = re.sub(
            r"^s/",
            "",
            normalized,
            flags=re.IGNORECASE,
        )

        normalized = normalized.removeprefix("@")
        normalized = normalized.split("?", 1)[0]
        normalized = normalized.split("/", 1)[0]

        return normalized.strip()

@staticmethod
    def _extract_image(node: Tag) -> str:
        """Извлекает прямую ссылку на фотографию публикации."""
        photo = node.select_one(
            ".tgme_widget_message_photo_wrap"
        )

        if photo is not None:
            style = html.unescape(
                str(photo.get("style", ""))
            )

            match = re.search(
                r"background-image\s*:\s*url\(\s*"
                r"(?:['\"])?(.+?)(?:['\"])?\s*\)",
                style,
                flags=re.IGNORECASE,
            )

            if match:
                image_url = match.group(1).strip(
                    " \t\r\n'\""
                )

                image_url = html.unescape(image_url)
                image_url = image_url.replace("\\/", "/")

                if image_url.startswith("//"):
                    image_url = "https:" + image_url

                return urljoin(
                    "https://t.me/",
                    image_url,
                )

        image = node.select_one(
            ".tgme_widget_message_document_thumb img, "
            ".tgme_widget_message_video_thumb img"
        )

        if image is not None:
            image_url = html.unescape(
                str(image.get("src", "")).strip()
            )

            if image_url.startswith("//"):
                image_url = "https:" + image_url

            return urljoin(
                "https://t.me/",
                image_url,
            )

        return ""

@staticmethod
    def _make_message_id(source_url: str) -> int:
        """Создаёт стабильный числовой идентификатор сообщения."""
        digest = hashlib.sha256(
            source_url.encode("utf-8")
        ).hexdigest()

        return int(digest[:12], 16)
