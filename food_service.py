from __future__ import annotations

from food_post import process_recipe
from food_telegram import send_food_message
from sources.food_source import FoodPost


def publish_recipe(post: FoodPost) -> str:
    """
    Полный цикл обработки и публикации рецепта.
    """

    result = process_recipe(
        text=post.text,
        message_id=post.message_id,
        source_url=post.source_url,
        image_url=post.image_url,
    )

    if result.duplicate:
        return result.text

    if not result.success:
        return result.text

    published_message_id = send_food_message(
        text=result.text,
        image_url=post.image_url,
    )

    return (
        "Рецепт опубликован в Food Radar. "
        f"message_id: {published_message_id}"
    ) 
