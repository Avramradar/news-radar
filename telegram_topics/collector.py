"""Автономный сборщик тематических Telegram-новостей."""

from __future__ import annotations

import html
import json
import os
from pathlib import Path

import requests

from filter import MilitaryFilter
from parser import TelegramPost, TelegramPublicParser


BASE_DIR = Path(__file__).resolve().parent
TOPIC_DIR = BASE_DIR / "military"

CHANNELS_FILE = TOPIC_DIR / "channels.txt"
CONFIG_FILE = TOPIC_DIR / "config.json"

TELEGRAM_TIMEOUT = 20
MAX_MESSAGE_LENGTH = 3900


def load_lines(path: Path) -> list[str]:
    """Читает непустые строки файла, игнорируя комментарии."""
    if not path.exists():
        print(f"Файл не найден: {path}")
        return []

    result: list[str] = []

    for raw_line in path.read_text(
        encoding="utf-8",
    ).splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        result.append(line)

    return list(dict.fromkeys(result))


def load_config(path: Path) -> dict:
    """Загружает настройки тематического канала."""
    if not path.exists():
        raise FileNotFoundError(
            f"Файл конфигурации не найден: {path}"
        )

    config = json.loads(
        path.read_text(encoding="utf-8")
    )

    target_channel = str(
        config.get("target_channel", "")
    ).strip()

    posts_per_channel = int(
        config.get("posts_per_channel", 10)
    )

    if not target_channel:
        raise ValueError(
            "В config.json не указан target_channel."
        )

    if posts_per_channel < 1:
        raise ValueError(
            "posts_per_channel должен быть больше нуля."
        )

    return {
        "target_channel": target_channel,
        "posts_per_channel": posts_per_channel,
    }


def get_bot_token() -> str:
    """Получает токен Telegram-бота из переменных окружения."""
    possible_names = (
        "TELEGRAM_BOT_TOKEN",
        "NEWS_BOT_TOKEN",
        "BOT_TOKEN",
    )

    for variable_name in possible_names:
        token = os.getenv(variable_name, "").strip()

        if token:
            print(
                "Токен Telegram найден в переменной: "
                f"{variable_name}"
            )
            return token

    return ""


def format_post(post: TelegramPost) -> str:
    """Формирует сообщение для тематического канала."""
    source_name = f"@{post.channel}"
    text = post.text.strip()

    if len(text) > MAX_MESSAGE_LENGTH:
        text = text[:MAX_MESSAGE_LENGTH].rstrip() + "…"

    return (
        f"{html.escape(text)}\n\n"
        f"Источник: "
        f'<a href="{html.escape(post.source_url)}">'
        f"{html.escape(source_name)}</a>"
    )


def publish_post(
    token: str,
    target_channel: str,
    post: TelegramPost,
) -> bool:
    """Публикует одно сообщение в целевой Telegram-канал."""
    api_url = (
        f"https://api.telegram.org/"
        f"bot{token}/sendMessage"
    )

    response = requests.post(
        api_url,
        timeout=TELEGRAM_TIMEOUT,
        data={
            "chat_id": target_channel,
            "text": format_post(post),
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
    )

    if response.ok:
        print(
            f"Опубликовано: @{post.channel}; "
            f"{post.source_url}"
        )
        return True

    print(
        "Ошибка публикации: "
        f"HTTP {response.status_code}; "
        f"{response.text}"
    )
    return False


def main() -> None:
    """Запускает полный тематический конвейер."""
    print("Запуск Telegram Military Collector.")

    try:
        config = load_config(CONFIG_FILE)
    except Exception as error:
        print(f"Ошибка конфигурации: {error}")
        return

    channels = load_lines(CHANNELS_FILE)

    if not channels:
        print("В channels.txt нет Telegram-каналов.")
        return

    token = get_bot_token()

    if not token:
        print(
            "Токен Telegram-бота не найден. "
            "Добавьте BOT_TOKEN в GitHub Secrets."
        )
        return

    target_channel = config["target_channel"]
    posts_per_channel = config["posts_per_channel"]

    print(f"Целевой канал: {target_channel}")
    print(f"Каналов для проверки: {len(channels)}")
    print(
        "Сообщений на один источник: "
        f"{posts_per_channel}"
    )

    parser = TelegramPublicParser(
        posts_per_channel=posts_per_channel,
    )

    military_filter = MilitaryFilter(
        topic_dir=str(TOPIC_DIR),
    )

    posts = parser.fetch_channels(channels)

    if not posts:
        print("Парсер не получил ни одной публикации.")
        return

    print(
        f"Всего получено публикаций: {len(posts)}"
    )

    filtered_posts: list[TelegramPost] = []
    seen_message_ids: set[int] = set()

    for post in posts:
        if post.message_id in seen_message_ids:
            continue

        seen_message_ids.add(post.message_id)

        if military_filter.check(post):
            filtered_posts.append(post)

    print(
        "После тематического фильтра осталось: "
        f"{len(filtered_posts)}"
    )

    published_count = 0

    for post in filtered_posts:
        try:
            if publish_post(
                token=token,
                target_channel=target_channel,
                post=post,
            ):
                published_count += 1
        except Exception as error:
            print(
                f"Ошибка отправки {post.source_url}: "
                f"{error}"
            )

    print(
        "Работа завершена. "
        f"Опубликовано сообщений: {published_count}"
    )


if __name__ == "__main__":
    main()
