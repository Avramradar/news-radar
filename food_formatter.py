from food_models import Recipe


STARS = {
    1: "⭐",
    2: "⭐⭐",
    3: "⭐⭐⭐",
}


def format_recipe(recipe: Recipe) -> str:
    """Формирует красивый текст рецепта для публикации."""

    stars = STARS.get(recipe.difficulty, "⭐")

    return (
        f"🍽 {recipe.title}\n\n"
        f"{stars}\n"
        f"📂 Категория: {recipe.category}\n\n"
        f"🔗 Полный рецепт:\n"
        f"{recipe.source_url}"
    )
