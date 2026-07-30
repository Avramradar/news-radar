"""Автономный сборщик тематических Telegram-новостей."""

from __future__ import annotations

import html
import json
import os
from pathlib import Path
from typing import Any

import requests

from filter import MilitaryFilter
from parser import TelegramPost, TelegramPublicParser


BASE_DIR = Path(__file__).resolve().parent
TOPIC_DIR = BASE_DIR / "military"

CHANNELS_FILE = TOPIC_DIR / "channels.txt"
CONFIG_FILE = TOPIC_DIR / "config.json"
STATE_FILE = TOPIC_DIR / "state.json"

TELEGRAM_TIMEOUT = 20
MAX_MESSAGE_LENGTH = 3900
MAX_STATE_ITEMS = 5000
DEFAULT_MAX_POSTS_PER_RUN = 3


def load_lines(path: Path) -> list[str]:
    """Читает строки файла, пропуская комментарии и пустые строки."""
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


def load_config(path: Path) -> dict[str, Any]:
    """Загружает и проверяет настройки тематического канала."""
    if not path.exists():
        raise FileNotFoundError(
            f"Файл конфигурации не найден: {path}"
        )

    raw_config = json.loads(
        path.read_text(encoding="utf-8")
    )

    target_channel = str(
        raw_config.get("target_channel", "")
    ).strip()

    posts_per_channel = int(
        raw_config.get("posts_per_channel", 10)
    )

    max_posts_per_run = int(
        raw_config.get(
            "max_posts_per_run",
            DEFAULT_MAX_POSTS_PER_RUN,
        )
    )

    if not target_channel:
        raise ValueError(
            "В config.json не указан target_channel."
        )

    if posts_per_channel < 1:
        raise ValueError(
            "posts_per_channel должен быть больше нуля."
        )

    if max_posts_per_run < 1:
        raise ValueError(
            "max_posts_per_run должен быть больше нуля."
        )

    return {
        "target_channel": target_channel,
        "posts_per_channel": posts_per_channel,
        "max_posts_per_run": max_posts_per_run,
    }


def load_state(path: Path) -> set[int]:
    """Загружает ID ранее опубликованных Telegram-сообщений."""
    if not path.exists():
        return set()

    try:
        raw_state = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as error:
        print(
            f"Не удалось прочитать state.json: {error}"
        )
        return set()

    raw_ids = raw_state.get(
        "published_message_ids",
        [],
    )

    if not isinstance(raw_ids, list):
        print(
            "Некорректный state.json: "
            "published_message_ids должен быть списком."
        )
        return set()

    published_ids: set[int] = set()

    for raw_id in raw_ids:
        try:
            published_ids.add(int(raw_id))
        except (TypeError, ValueError):
            continue

    return published_ids


def save_state(
    path: Path,
    published_ids: set[int],
) -> None:
    """Сохраняет состояние атомарно, чтобы файл не повредился."""
    limited_ids = sorted(
        published_ids,
    )[-MAX_STATE_ITEMS:]

    state = {
        "published_message_ids": limited_ids,
    }

    temporary_path = path.with_suffix(".tmp")

    temporary_path.write_text(
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary_path.replace(path)


def get_bot_token() -> str:
    """Получает токен Telegram-бота из переменных окружения."""
    possible_names = (
        "BOT_TOKEN",
        "TELEGRAM_BOT_TOKEN",
        "NEWS_BOT_TOKEN",
    )

    for variable_name in possible_names:
        token = os.getenv(
            variable_name,
            "",
        ).strip()

        if token:
            print(
                "Токен Telegram найден в переменной: "
                f"{variable_name}"
            )
            return token

    return ""


def format_post(post: TelegramPost) -> str:
    """Формирует публикацию для тематического канала."""
    source_name = f"@{post.channel}"
    text = post.text.strip()

    if len(text) > MAX_MESSAGE_LENGTH:
        text = (
            text[:MAX_MESSAGE_LENGTH].rstrip()
            + "…"
        )

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
    """Публикует одно сообщение через Telegram Bot API."""
    api_url = (
        "https://api.telegram.org/"
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
            f"Опубликовано: {post.source_url}"
        )
        return True

    print(
        "Ошибка публикации: "
        f"HTTP {response.status_code}; "
        f"{response.text}"
    )
    return False


def select_new_posts(
    posts: list[TelegramPost],
    military_filter: MilitaryFilter,
    published_ids: set[int],
) -> list[TelegramPost]:
    """Оставляет только новые сообщения, прошедшие фильтр."""
    selected: list[TelegramPost] = []
    current_run_ids: set[int] = set()

    for post in posts:
        if post.message_id in published_ids:
            continue

        if post.message_id in current_run_ids:
            continue

        current_run_ids.add(post.message_id)

        if military_filter.check(post):
            selected.append(post)

    return selected


def main() -> None:
    """Запускает тематический Telegram-конвейер."""
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
            "Проверьте секрет BOT_TOKEN."
        )
        return

    target_channel = str(
        config["target_channel"]
    )

    posts_per_channel = int(
        config["posts_per_channel"]
    )

    max_posts_per_run = int(
        config["max_posts_per_run"]
    )

    published_ids = load_state(STATE_FILE)

    print(f"Целевой канал: {target_channel}")
    print(f"Источников: {len(channels)}")
    print(
        "Ранее опубликованных ID: "
        f"{len(published_ids)}"
    )

    parser = TelegramPublicParser(
        posts_per_channel=posts_per_channel,
    )

    military_filter = MilitaryFilter(
        topic_dir=str(TOPIC_DIR),
    )

    posts = parser.fetch_channels(channels)

    if not posts:
        print("Парсер не получил публикаций.")
        return

    print(
        f"Всего получено публикаций: {len(posts)}"
    )

    selected_posts = select_new_posts(
        posts=posts,
        military_filter=military_filter,
        published_ids=published_ids,
    )

    print(
        "Новых публикаций после фильтра: "
        f"{len(selected_posts)}"
    )

    posts_to_publish = selected_posts[
        -max_posts_per_run:
    ]

    published_count = 0

    for post in posts_to_publish:
        try:
            success = publish_post(
                token=token,
                target_channel=target_channel,
                post=post,
            )
        except Exception as error:
            print(
                f"Ошибка отправки {post.source_url}: "
                f"{error}"
            )
            continue

        if not success:
            continue

        published_ids.add(post.message_id)
        published_count += 1

        try:
            save_state(
                STATE_FILE,
                published_ids,
            )
        except OSError as error:
            print(
                "Сообщение опубликовано, но состояние "
                f"не сохранено: {error}"
            )
            return

    print(
        "Работа завершена. "
        f"Опубликовано сообщений: {published_count}"
    )


if __name__ == "__main__":
    main()
