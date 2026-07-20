from __future__ import annotations

import os
from dataclasses import dataclass

from .base_source import BaseSource


@dataclass
class FoodPost:
    """Необработанная публикация с рецептом."""

    text: str
    message_id: int
    source_url: str
    image_url: str = ""


class FoodSource(BaseSource):
    """
    Получает рецепт из переменных окружения GitHub Actions.
    """

    def fetch(self) -> list[FoodPost]:
        text = os.getenv("FOOD_TEXT", "").strip()
        source_url = os.getenv("FOOD_SOURCE_URL", "").strip()
        image_url = os.getenv("FOOD_IMAGE_URL", "").strip()
        message_id_text = os.getenv("FOOD_MESSAGE_ID", "").strip()

        if not text:
            return []

        if not source_url:
            raise ValueError(
                "Переменная FOOD_SOURCE_URL не заполнена."
            )

        if not message_id_text:
            raise ValueError(
                "Переменная FOOD_MESSAGE_ID не заполнена."
            )

        try:
            message_id = int(message_id_text)
        except ValueError as error:
            raise ValueError(
                "FOOD_MESSAGE_ID должен быть целым числом."
            ) from error

        return [
            FoodPost(
                text=text,
                message_id=message_id,
                source_url=source_url,
                image_url=image_url,
            )
        ]
