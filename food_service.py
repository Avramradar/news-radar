from __future__ import annotations

import re

from food_post import process_recipe
from food_telegram import send_food_message
from sources.food_source import FoodPost


# Минимальная длина полноценного рецепта.
MIN_RECIPE_LENGTH = 350

# Минимальное количество содержательных строк.
MIN_RECIPE_LINES = 5

# Минимальное количество кулинарных признаков в тексте.
MIN_FOOD_MARKERS = 2


FOOD_MARKERS = (
    "ингредиент",
    "состав",
    "приготов",
    "рецепт",
    "добав",
    "нареж",
    "смеш",
    "перемеш",
    "варить",
    "варим",
    "отвар",
    "обжар",
    "жарить",
    "жарим",
    "выпек",
    "запек",
    "тушить",
    "тушим",
    "маринов",
    "тесто",
    "масло",
    "мука",
    "соль",
    "сахар",
    "перец",
    "духовк",
    "сковород",
    "кастрюл",
    "минут",
    "грамм",
    "мл",
)


def normalize_source_text(text: str) -> str:
    """
    Очищает исходный текст перед проверкой и публикацией.
    Полезное содержимое рецепта не обрезается.
    """
    if not text:
        return ""

    text = text.strip()

    # Удаляем невидимые символы.
    text = text.replace("\u200b", "")
    text = text.replace("\ufeff", "")

    # Удаляем технические теги сложности.
    text = re.sub(
        r"#FR_LEVEL_[123]",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Убираем отдельную ссылку в конце текста.
    # Ссылка на источник всё равно будет добавлена форматтером.
    text = re.sub(
        r"\n\s*https?://\S+\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Убираем слишком большое количество пустых строк.
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    # Убираем пробелы перед переносами строк.
    text = re.sub(
        r"[ \t]+\n",
        "\n",
        text,
    )

    return text.strip()


def count_meaningful_lines(text: str) -> int:
    """
    Считает строки, в которых есть полезное содержимое.
    """
    return len(
        [
            line
            for line in text.splitlines()
            if len(line.strip()) >= 3
        ]
    )


def count_food_markers(text: str) -> int:
    """
    Считает количество кулинарных признаков.
    Один признак учитывается только один раз.
    """
    lowered = text.lower()

    return sum(
        1
        for marker in FOOD_MARKERS
        if marker in lowered
    )


def has_recipe_structure(text: str) -> bool:
    """
    Проверяет наличие характерной структуры рецепта:
    ингредиентов, шагов или единиц измерения.
    """
    lowered = text.lower()

    section_markers = (
        "ингредиенты",
        "состав:",
        "приготовление",
        "как приготовить",
        "способ приготовления",
        "пошаговый рецепт",
        "инструкция",
    )

    if any(marker in lowered for marker in section_markers):
        return True

    # Ищем пронумерованные шаги.
    numbered_steps = re.findall(
        r"(?m)^\s*\d+[\.\)]\s+\S+",
        text,
    )

    if len(numbered_steps) >= 2:
        return True

    # Ищем строки, похожие на ингредиенты.
    ingredient_lines = re.findall(
        r"(?im)^\s*[•\-–—]?\s*"
        r".{2,50}\s+[—\-:]\s*"
        r"\d+(?:[.,]\d+)?\s*"
        r"(?:г|гр|кг|мл|л|шт|ст\.?\s*л|ч\.?\s*л)",
        text,
    )

    return len(ingredient_lines) >= 2


def is_recipe_complete(text: str) -> bool:
    """
    Проверяет, достаточно ли рецепт наполнен
    для публикации в Food Radar.
    """
    if not text:
        return False

    clean_text = text.strip()

    if len(clean_text) < MIN_RECIPE_LENGTH:
        return False

    if count_meaningful_lines(clean_text) < MIN_RECIPE_LINES:
        return False

    if count_food_markers(clean_text) < MIN_FOOD_MARKERS:
        return False

    if not has_recipe_structure(clean_text):
        return False

    return True


def publish_recipe(post: FoodPost) -> str:
    """
    Проверяет, обрабатывает и публикует один рецепт.

    Неполные публикации пропускаются.
    Дубликаты повторно не публикуются.
    """
    source_text = normalize_source_text(post.text)

    if not is_recipe_complete(source_text):
        message = (
            "Пропуск: рецепт слишком короткий "
            "или не содержит полного приготовления."
        )

        print(
            "Recipe skipped: incomplete source text. "
            f"message_id={post.message_id}, "
            f"length={len(source_text)}, "
            f"lines={count_meaningful_lines(source_text)}, "
            f"markers={count_food_markers(source_text)}"
        )

        return message

    result = process_recipe(
        text=source_text,
        message_id=post.message_id,
        source_url=post.source_url,
        image_url=post.image_url,
    )

    if result.duplicate:
        print(
            "Recipe skipped: duplicate. "
            f"message_id={post.message_id}"
        )

        return result.text

    published_message_id = send_food_message(
        text=result.text,
        image_url=post.image_url,
    )

    print(
        "Recipe published successfully. "
        f"source_message_id={post.message_id}, "
        f"telegram_message_id={published_message_id}"
    )

    return result.text
