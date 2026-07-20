from __future__ import annotations

from food_post import process_recipe
from food_telegram import send_food_message
from sources.food_source import FoodPost


def publish_recipe(post: FoodPost) -> str:
    """
    Полный цикл обработки и публикации рецепта.
    """

    formatted_text = process_recipe(
        text=post.text,
        message_id=post.message_id,
        source_url=post.source_url,
        image_url=post.image_url,
    )

    if formatted_text == "Рецепт уже был сохранён.":
        return formatted_text

    send_food_message(
        text=formatted_text,
        image_url=post.image_url,
    )

    return "OK"
