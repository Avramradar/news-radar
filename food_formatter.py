from food_models import Recipe


STARS = {
    1: "⭐",
    2: "⭐⭐",
    3: "⭐⭐⭐",
}


def format_recipe(recipe: Recipe) -> str:
    """Формирует полный красивый пост рецепта."""

    stars = STARS.get(recipe.difficulty, "⭐")

    return (
        f"🍽 {recipe.title}\n\n"
        f"⭐ Сложность: {stars}\n"
        f"📂 Категория: {recipe.category}\n\n"
        f"{recipe.content}\n\n"
        f"🔗 Источник:\n{recipe.source_url}"
    )
