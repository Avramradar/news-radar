from __future__ import annotations

import os

import requests


BOT_TOKEN = os.environ["BOT_TOKEN"]
FOOD_CHANNEL = os.getenv("FOOD_CHANNEL", "@FoodRadarDaily")


def send_food_message(text: str, image_url: str = "") -> int:
    """
    Публикует сообщение в Food Radar.
    Возвращает message_id опубликованного поста.
    """

    if image_url:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
            data={
                "chat_id": FOOD_CHANNEL,
                "photo": image_url,
                "caption": text[:1024],
                "parse_mode": "HTML",
            },
            timeout=30,
        )
    else:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={
                "chat_id": FOOD_CHANNEL,
                "text": text[:4096],
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=30,
        )
    print("Telegram response:", response.text)
    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(
            f"Telegram вернул ошибку: {result}"
        )

    return int(result["result"]["message_id"])
