from __future__ import annotations

import html
import re

from food_models import Recipe


STARS = {
    1: "⭐",
    2: "⭐⭐",
    3: "⭐⭐⭐",
}


SECTION_MARKERS = (
    "ингредиенты",
    "состав",
    "приготовление",
    "способ приготовления",
    "как приготовить",
    "пошаговый рецепт",
    "инструкция",
    "совет",
    "секрет",
    "примечание",
)


def clean_text(text: str) -> str:
    """Очищает исходный текст рецепта."""
    if not text:
        return ""

    text = html.unescape(text)

    # Заменяем основные HTML-разделители строк.
    text = re.sub(
        r"<\s*(br|p|div|li)[^>]*>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    # Удаляем оставшиеся HTML-теги.
    text = re.sub(r"<[^>]+>", "", text)

    # Удаляем технические теги Food Radar.
    text = re.sub(
        r"#FR_LEVEL_[123]",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Убираем лишние пробелы.
    text = re.sub(r"[ \t]+", " ", text)

    # Убираем пробелы в начале и конце строк.
    lines = [line.strip() for line in text.splitlines()]

    # Удаляем подряд идущие пустые строки.
    cleaned_lines: list[str] = []
    previous_empty = False

    for line in lines:
        is_empty = not line

        if is_empty and previous_empty:
            continue

        cleaned_lines.append(line)
        previous_empty = is_empty

    return "\n".join(cleaned_lines).strip()


def remove_duplicate_title(text: str, title: str) -> str:
    """Не позволяет названию блюда повторяться дважды."""
    lines = text.splitlines()

    if not lines:
        return text

    first_line = lines[0].strip()
    normalized_first = re.sub(r"\W+", "", first_line.lower())
    normalized_title = re.sub(r"\W+", "", title.lower())

    if normalized_first and normalized_first == normalized_title:
        return "\n".join(lines[1:]).strip()

    return text


def normalize_headings(text: str) -> str:
    """Приводит названия разделов к единому оформлению."""
    replacements = (
        (
            r"(?im)^\s*(ингредиенты|состав)\s*:?\s*$",
            "🛒 ИНГРЕДИЕНТЫ",
        ),
        (
            r"(?im)^\s*(приготовление|способ приготовления|"
            r"как приготовить|пошаговый рецепт|инструкция)\s*:?\s*$",
            "👨‍🍳 ПРИГОТОВЛЕНИЕ",
        ),
        (
            r"(?im)^\s*(совет|советы|секрет|секрет повара|"
            r"примечание)\s*:?\s*$",
            "💡 СОВЕТ",
        ),
    )

    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)

    return text


def format_ingredient_lines(text: str) -> str:
    """Оформляет похожие на ингредиенты строки маркерами."""
    lines = text.splitlines()
    result: list[str] = []
    inside_ingredients = False

    for line in lines:
        stripped = line.strip()

        if stripped == "🛒 ИНГРЕДИЕНТЫ":
            inside_ingredients = True
            result.append(stripped)
            continue

        if stripped in (
            "👨‍🍳 ПРИГОТОВЛЕНИЕ",
            "💡 СОВЕТ",
        ):
            inside_ingredients = False
            result.append(stripped)
            continue

        if (
            inside_ingredients
            and stripped
            and not re.match(r"^[•\-–—\d]", stripped)
        ):
            stripped = f"• {stripped}"

        result.append(stripped)

    return "\n".join(result)


def format_cooking_steps(text: str) -> str:
    """Нумерует шаги приготовления, если они ещё не пронумерованы."""
    lines = text.splitlines()
    result: list[str] = []
    inside_cooking = False
    step_number = 1

    for line in lines:
        stripped = line.strip()

        if stripped == "👨‍🍳 ПРИГОТОВЛЕНИЕ":
            inside_cooking = True
            step_number = 1
            result.append(stripped)
            continue

        if stripped in (
            "🛒 ИНГРЕДИЕНТЫ",
            "💡 СОВЕТ",
        ):
            inside_cooking = False
            result.append(stripped)
            continue

        if inside_cooking and stripped:
            already_numbered = re.match(
                r"^\d+[\.\)]\s+",
                stripped,
            )

            if not already_numbered:
                stripped = f"{step_number}. {stripped}"

            step_number += 1

        result.append(stripped)

    return "\n".join(result)


def extract_metadata(text: str) -> tuple[list[str], str]:
    """Извлекает время приготовления и количество порций."""
    metadata: list[str] = []

    time_match = re.search(
        r"(?im)^\s*(?:время(?: приготовления)?|готовить)\s*:"
        r"\s*(.+)$",
        text,
    )

    if time_match:
        metadata.append(f"⏱ Время: {time_match.group(1).strip()}")
        text = text.replace(time_match.group(0), "")

    portions_match = re.search(
        r"(?im)^\s*(?:порции|количество порций|выход)\s*:"
        r"\s*(.+)$",
        text,
    )

    if portions_match:
        metadata.append(
            f"👥 Порции: {portions_match.group(1).strip()}"
        )
        text = text.replace(portions_match.group(0), "")

    return metadata, text.strip()


def format_recipe(recipe: Recipe) -> str:
    """Формирует полный структурированный пост рецепта."""
    stars = STARS.get(recipe.difficulty, "⭐")

    content = clean_text(recipe.content)
    content = remove_duplicate_title(content, recipe.title)
    metadata, content = extract_metadata(content)
    content = normalize_headings(content)
    content = format_ingredient_lines(content)
    content = format_cooking_steps(content)

    header_lines = [
        f"🍽 {recipe.title}",
        "",
        f"⭐ Сложность: {stars}",
        f"📂 Категория: {recipe.category}",
    ]

    if metadata:
        header_lines.extend(metadata)

    post_parts = [
    "\n".join(header_lines),
    content,
    f"🔗 Источник:\n{recipe.source_url}",
    (
        "━━━━━━━━━━━━━━\n"
        "🍽 Больше рецептов в Food Radar:\n"
        "https://t.me/FoodRadarDaily"
    ),
]

    return "\n\n".join(
        part.strip()
        for part in post_parts
        if part and part.strip()
    )
