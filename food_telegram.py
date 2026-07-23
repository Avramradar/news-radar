from __future__ import annotations

import json
import os

import requests


BOT_TOKEN = os.environ["BOT_TOKEN"]

FOOD_CHANNEL = os.getenv(
    "FOOD_CHANNEL",
    "@FoodRadarDaily",
)

RADAR_FRIDGE_BOT_URL = os.getenv(
    "RADAR_FRIDGE_BOT_URL",
    "https://t.me/RadarFridgebot",
)

TELEGRAM_TEXT_LIMIT = 3900
PHOTO_CAPTION_LIMIT = 900


def build_fridge_keyboard() -> str:
    """
    Создаёт inline-кнопку для перехода
    в бот RadarFridge.
    """
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "🥕 Найти рецепт по продуктам",
                    "url": RADAR_FRIDGE_BOT_URL,
                }
            ]
        ]
    }

    return json.dumps(
        keyboard,
        ensure_ascii=False,
    )


def split_text(
    text: str,
    limit: int = TELEGRAM_TEXT_LIMIT,
) -> list[str]:
    """
    Делит длинный рецепт на несколько сообщений,
    стараясь не разрывать абзацы и слова.
    """
    text = text.strip()

    if not text:
        return []

    if len(text) <= limit:
        return [text]

    parts: list[str] = []
    remaining = text

    while len(remaining) > limit:
        split_position = remaining.rfind(
            "\n\n",
            0,
            limit,
        )

        if split_position < limit // 2:
            split_position = remaining.rfind(
                "\n",
                0,
                limit,
            )

        if split_position < limit // 2:
            split_position = remaining.rfind(
                ". ",
                0,
                limit,
            )

            if split_position != -1:
                split_position += 1

        if split_position < limit // 2:
            split_position = remaining.rfind(
                " ",
                0,
                limit,
            )

        if split_position <= 0:
            split_position = limit

        part = remaining[:split_position].strip()

        if part:
            parts.append(part)

        remaining = remaining[
            split_position:
        ].strip()

    if remaining:
        parts.append(remaining)

    return parts


def send_text_message(
    text: str,
    show_fridge_button: bool = False,
) -> int:
    """
    Отправляет одно текстовое сообщение
    в канал Food Radar.
    """
    data = {
        "chat_id": FOOD_CHANNEL,
        "text": text,
        "disable_web_page_preview": True,
    }

    if show_fridge_button:
        data["reply_markup"] = build_fridge_keyboard()

    response = requests.post(
        (
            f"https://api.telegram.org/"
            f"bot{BOT_TOKEN}/sendMessage"
        ),
        data=data,
        timeout=30,
    )

    print(
        "Telegram text response:",
        response.text,
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(
            f"Telegram вернул ошибку: {result}"
        )

    return int(
        result["result"]["message_id"]
    )


def send_photo_message(
    image_url: str,
    caption: str,
) -> int | None:
    """
    Отправляет фотографию рецепта
    вместе с кнопкой RadarFridge.

    При ошибке возвращает None,
    чтобы рецепт можно было отправить текстом.
    """
    response = requests.post(
        (
            f"https://api.telegram.org/"
            f"bot{BOT_TOKEN}/sendPhoto"
        ),
        data={
            "chat_id": FOOD_CHANNEL,
            "photo": image_url,
            "caption": caption,
            "reply_markup": build_fridge_keyboard(),
        },
        timeout=30,
    )

    print(
        "Telegram photo response:",
        response.text,
    )

    if not response.ok:
        print(
            "Photo failed, recipe will "
            "be sent as text:",
            response.text,
        )
        return None

    result = response.json()

    if not result.get("ok"):
        print(
            "Telegram rejected photo:",
            result,
        )
        return None

    return int(
        result["result"]["message_id"]
    )


def send_food_message(
    text: str,
    image_url: str = "",
) -> int:
    """
    Публикует фотографию и полный текст рецепта.

    Если фотография успешно отправлена,
    кнопка RadarFridge появляется под фотографией.

    Если фотографии нет или отправка не удалась,
    кнопка появляется под последней частью текста.
    """
    text = (text or "").strip()
    image_url = (image_url or "").strip()

    if not text:
        raise ValueError(
            "Нельзя отправить пустой рецепт."
        )

    first_message_id: int | None = None
    photo_was_sent = False

    if image_url:
        first_line = text.splitlines()[0].strip()

        photo_caption = first_line[
            :PHOTO_CAPTION_LIMIT
        ]

        photo_message_id = send_photo_message(
            image_url=image_url,
            caption=photo_caption,
        )

        if photo_message_id is not None:
            first_message_id = photo_message_id
            photo_was_sent = True

    parts = split_text(text)

    if not parts:
        raise RuntimeError(
            "Не удалось подготовить текст рецепта."
        )

    total_parts = len(parts)

    for number, part in enumerate(
        parts,
        start=1,
    ):
        if number > 1:
            part = (
                "Продолжение рецепта 👇\n\n"
                f"{part}"
            )

        is_last_part = number == total_parts

        # Если фото успешно опубликовано,
        # кнопка уже находится под ним.
        # Иначе ставим кнопку под последним текстом.
        show_button = (
            is_last_part
            and not photo_was_sent
        )

        message_id = send_text_message(
            text=part,
            show_fridge_button=show_button,
        )

        if first_message_id is None:
            first_message_id = message_id

    if first_message_id is None:
        raise RuntimeError(
            "Telegram не опубликовал рецепт."
        )

    return first_message_id
