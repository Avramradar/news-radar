from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests


BOT_TOKEN = os.environ["BOT_TOKEN"]

FOOD_CHANNEL = os.getenv(
    "FOOD_CHANNEL",
    "@FoodRadarDaily",
)

NEWS_CHANNEL = os.getenv(
    "NEWS_CHANNEL",
    "@newsRadar2026",
)

FOOD_STATE_FILE = Path(
    os.getenv(
        "FOOD_STATE_FILE",
        "food_state.json",
    )
)

REPOST_STATE_FILE = Path(
    os.getenv(
        "REPOST_STATE_FILE",
        "food_to_news_state.json",
    )
)


def load_json(
    path: Path,
    default: Any,
) -> Any:
    if not path.exists():
        return default

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )
    except (
        json.JSONDecodeError,
        OSError,
    ):
        return default


def save_json(
    path: Path,
    data: Any,
) -> None:
    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def find_message_ids(
    value: Any,
) -> list[int]:
    """
    Ищет Telegram message_id внутри food_state.json
    независимо от точной структуры файла.
    """
    message_ids: list[int] = []

    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = key.lower()

            if normalized_key in {
                "message_id",
                "telegram_message_id",
                "food_message_id",
            }:
                try:
                    message_ids.append(
                        int(item)
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    pass

            message_ids.extend(
                find_message_ids(item)
            )

    elif isinstance(value, list):
        for item in value:
            message_ids.extend(
                find_message_ids(item)
            )

    return message_ids


def forward_message(
    message_id: int,
) -> int:
    url = (
        "https://api.telegram.org/"
        f"bot{BOT_TOKEN}/forwardMessage"
    )

    response = requests.post(
        url,
        data={
            "chat_id": NEWS_CHANNEL,
            "from_chat_id": FOOD_CHANNEL,
            "message_id": message_id,
        },
        timeout=30,
    )

    print(
        "Telegram response:",
        response.text,
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(
            "Telegram вернул ошибку: "
            f"{result}"
        )

    return int(
        result["result"]["message_id"]
    )


def main() -> None:
    food_state = load_json(
        FOOD_STATE_FILE,
        {},
    )

    message_ids = find_message_ids(
        food_state
    )

    if not message_ids:
        print(
            "В food_state.json не найден "
            "message_id рецепта."
        )
        return

    latest_food_message_id = max(
        message_ids
    )

    repost_state = load_json(
        REPOST_STATE_FILE,
        {
            "copied_message_ids": [],
        },
    )

    copied_ids = {
        int(message_id)
        for message_id in repost_state.get(
            "copied_message_ids",
            [],
        )
    }

    if latest_food_message_id in copied_ids:
        print(
            "Этот рецепт уже был отправлен "
            "в News Radar:",
            latest_food_message_id,
        )
        return

    print(
        "Отправляем рецепт в News Radar:",
        latest_food_message_id,
    )

    news_message_id = forward_message(
        latest_food_message_id
    )

    copied_ids.add(
        latest_food_message_id
    )

    save_json(
        REPOST_STATE_FILE,
        {
            "copied_message_ids": sorted(
                copied_ids
            ),
            "last_food_message_id": (
                latest_food_message_id
            ),
            "last_news_message_id": (
                news_message_id
            ),
        },
    )

    print(
        "Рецепт отправлен из Food Radar "
        "в News Radar.",
        "Food message_id:",
        latest_food_message_id,
        "News message_id:",
        news_message_id,
    )


if __name__ == "__main__":
    main()
