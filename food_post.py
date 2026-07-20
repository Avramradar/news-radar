from __future__ import annotations

from food_formatter import format_recipe
from food_parser import parse_recipe_post
from food_storage import load_storage, save_storage


def process_recipe(
    text: str,
    message_id: int,
    source_url: str,
    image_url: str = "",
) -> str:
    """
    Обрабатывает один рецепт и возвращает
    готовый текст для публикации.
    """

    recipe = parse_recipe_post(
        text=text,
        message_id=message_id,
        source_url=source_url,
        image_url=image_url,
    )

    storage = load_storage()

    storage["recipes"].append(recipe.__dict__)

    save_storage(storage)

    return format_recipe(recipe)
