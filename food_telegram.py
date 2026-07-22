from __future__ import annotations

import os

import requests


BOT_TOKEN = os.environ["BOT_TOKEN"]
FOOD_CHANNEL = os.getenv("FOOD_CHANNEL", "@FoodRadarDaily")

TELEGRAM_TEXT_LIMIT = 3900
PHOTO_CAPTION_LIMIT = 900


def split_text(text: str, limit: int = TELEGRAM_TEXT_LIMIT) -> list[str]:
    """
    Делит длинный рецепт на несколько сообщений,
    стараясь не разрывать абзацы и слова.
    """
    text = text.strip()

    if not text:
        return []

    if len(text) <= limit:
        return [text]

    parts = []
    remaining = text

    while len(remaining) > limit:
        split_position = remaining.rfind("\n\n", 0, limit)

        if split_position < limit // 2:
            split_position = remaining.rfind("\n", 0, limit)

        if split_position < limit // 2:
            split_position = remaining.rfind(". ", 0, limit)

            if split_position != -1:
                split_position += 1

        if split_position < limit // 2:
            split_position = remaining.rfind(" ", 0, limit)

        if split_position <= 0:
            split_position = limit

        part = remaining[:split_position].strip()

        if part:
            parts.append(part)

        remaining = remaining[split_position:].strip()

    if remaining:
        parts.append(remaining)

    return parts


def send_text_message(text: str) -> int:
    """Отправляет одно текстовое сообщение в Food Radar."""
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={
            "chat_id": FOOD_CHANNEL,
            "text": text,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )

    print("Telegram text response:", response.text)
    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(
            f"Telegram вернул ошибку: {result}"
        )

    return int(result["result"]["message_id"])


def send_food_message(text: str, image_url: str = "") -> int:
    """
    Публикует фотографию и полный текст рецепта.

    Длинный рецепт автоматически разделяется
    на несколько сообщений без обрезания.
    """
    text = (text or "").strip()

    if not text:
        raise ValueError("Нельзя отправить пустой рецепт.")

    first_message_id: int | None = None

    if image_url:
        first_line = text.splitlines()[0].strip()

        photo_caption = first_line[:PHOTO_CAPTION_LIMIT]

        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
            data={
                "chat_id": FOOD_CHANNEL,
                "photo": image_url,
                "caption": photo_caption,
            },
            timeout=30,
        )

        print("Telegram photo response:", response.text)

        if response.ok:
            result = response.json()

            if result.get("ok"):
                first_message_id = int(
                    result["result"]["message_id"]
                )
        else:
            print(
                "Photo failed, recipe will be sent as text:",
                response.text,
            )

    parts = split_text(text)

    for number, part in enumerate(parts, start=1):
        if number > 1:
            part = f"Продолжение рецепта 👇\n\n{part}"

        message_id = send_text_message(part)

        if first_message_id is None:
            first_message_id = message_id

    if first_message_id is None:
        raise RuntimeError("Telegram не опубликовал рецепт.")

    return first_message_id
