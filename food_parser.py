from __future__ import annotations

import re

from food_models import Recipe


DIFFICULTY_MAP = {
    "#FR_LEVEL_1": 1,
    "#FR_LEVEL_2": 2,
    "#FR_LEVEL_3": 3,
}


def extract_title(text: str) -> str:
    """Берёт название блюда из первой непустой строки."""
    for line in text.splitlines():
        clean_line = line.strip()

        if not clean_line:
            continue

        clean_line = re.sub(r"^[^\wА-Яа-яЁё]+", "", clean_line)
        return clean_line.strip()

    return "Без названия"


def extract_difficulty(text: str) -> int:
    """Определяет сложность рецепта по тегам и содержанию."""
    for tag, level in DIFFICULTY_MAP.items():
        if tag in text:
            return level

    lowered = text.lower()

    hard_words = (
        "сложный",
        "профессиональный",
        "су-вид",
        "темперировать",
        "ферментация",
        "многоэтапный",
        "оставить на ночь",
    )

    medium_words = (
        "духовка",
        "выпекать",
        "мариновать",
        "дрожжи",
        "тесто",
        "запекать",
        "тушить",
    )

    if any(word in lowered for word in hard_words):
        return 3

    if any(word in lowered for word in medium_words):
        return 2

    return 1 


def extract_category(text: str) -> str:
    """Определяет категорию по явной метке или ключевым словам."""
    match = re.search(
        r"Категория:\s*(.+)",
        text,
        flags=re.IGNORECASE,
    )

    if match:
        return match.group(1).strip()

    lowered = text.lower()

    categories = {
        "Десерт": (
            "десерт",
            "торт",
            "пирожное",
            "печенье",
            "крем",
            "мороженое",
            "шоколад",
        ),
        "Выпечка": (
            "выпечка",
            "пирог",
            "булочка",
            "хлеб",
            "тесто",
            "дрожжи",
        ),
        "Напиток": (
            "напиток",
            "коктейль",
            "лимонад",
            "кофе",
            "чай",
            "смузи",
        ),
        "Лайфхак": (
            "лайфхак",
            "как хранить",
            "как выбрать",
            "как очистить",
            "быстрый способ",
        ),
        "Совет": (
            "совет",
            "секрет повара",
            "кулинарный секрет",
            "полезно знать",
        ),
        "Салат": (
            "салат",
            "закуска",
        ),
        "Суп": (
            "суп",
            "борщ",
            "бульон",
            "солянка",
        ),
        "Основное блюдо": (
            "мясо",
            "рыба",
            "курица",
            "котлет",
            "паста",
            "плов",
            "гарнир",
        ),
    }

    for category, keywords in categories.items():
        if any(keyword in lowered for keyword in keywords):
            return category

    return "Рецепт" 


def parse_recipe_post(
    text: str,
    message_id: int,
    source_url: str,
    image_url: str = "",
) -> Recipe:
    """Преобразует текст публикации Food Radar в объект Recipe."""
    return Recipe(
        title=extract_title(text),
        difficulty=extract_difficulty(text),
        category=extract_category(text),
        source_url=source_url,
        image_url=image_url,
        message_id=message_id,
        published=True,
    )
