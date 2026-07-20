from __future__ import annotations

import os

from food_post import process_recipe
from food_telegram import send_food_message


def main() -> None:
    text = os.getenv("FOOD_TEXT", "").strip()
    source_url = os.getenv("FOOD_SOURCE_URL", "").strip()
    image_url = os.getenv("FOOD_IMAGE_URL", "").strip()
    message_id_text = os.getenv("FOOD_MESSAGE_ID", "0").strip()

    if not text:
        raise ValueError("Переменная FOOD_TEXT не заполнена.")

    if not source_url:
        raise ValueError("Переменная FOOD_SOURCE_URL не заполнена.")

    try:
        message_id = int(message_id_text)
    except ValueError as error:
        raise ValueError(
            "FOOD_MESSAGE_ID должен быть целым числом."
        ) from error

    formatted_text = process_recipe(
        text=text,
        message_id=message_id,
        source_url=source_url,
        image_url=image_url,
    )

    if formatted_text == "Рецепт уже был сохранён.":
        print(formatted_text)
        return

    published_message_id = send_food_message(
        text=formatted_text,
        image_url=image_url,
    )

    print(
        "Рецепт опубликован в Food Radar. "
        f"message_id: {published_message_id}"
    )


if __name__ == "__main__":
    main()
