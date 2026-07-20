from __future__ import annotations

import os

from food_post import process_recipe


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

    result = process_recipe(
        text=text,
        message_id=message_id,
        source_url=source_url,
        image_url=image_url,
    )

    print(result)


if __name__ == "__main__":
    main()
