from __future__ import annotations

from food_formatter import format_recipe
from food_parser import parse_recipe_post
from food_storage import load_storage, save_storage
from food_result import ProcessResult


def process_recipe(
    text: str,
    message_id: int,
    source_url: str,
    image_url: str = "",
) -> ProcessResult: 
    """
    Обрабатывает один рецепт, сохраняет его
    и возвращает текст для публикации.
    """

    storage = load_storage()

    for saved_recipe in storage["recipes"]:
        if saved_recipe.get("message_id") == message_id:
            return "Рецепт уже был сохранён."

    recipe = parse_recipe_post(
        text=text,
        message_id=message_id,
        source_url=source_url,
        image_url=image_url,
    )

    storage["recipes"].append(recipe.__dict__)

    save_storage(storage)

    return format_recipe(recipe)
