from __future__ import annotations

import re

from food_post import process_recipe
from food_telegram import send_food_message
from sources.food_source import FoodPost


# Минимальная длина текста рецепта.
# Уменьшено с 350, потому что некоторые полноценные рецепты
# приходят в компактном формате.
MIN_RECIPE_LENGTH = 180

# Минимальное количество содержательных строк.
# Допускаем рецепты, записанные в несколько длинных абзацев.
MIN_RECIPE_LINES = 2

# Минимальное количество кулинарных признаков.
MIN_FOOD_MARKERS = 1


FOOD_MARKERS = (
    "ингредиент",
    "состав",
    "продукт",
    "понадобится",
    "приготов",
    "рецепт",
    "добав",
    "нареж",
    "измельч",
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


INGREDIENT_SECTION_MARKERS = (
    "ингредиенты",
    "ингредиент",
    "состав:",
    "состав блюда",
    "продукты:",
    "необходимые продукты",
    "нам понадобится",
    "вам понадобится",
    "понадобится:",
)


COOKING_SECTION_MARKERS = (
    "приготовление",
    "как приготовить",
    "способ приготовления",
    "пошаговый рецепт",
    "инструкция",
    "готовим",
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
    text = text.replace("\xa0", " ")

    # Удаляем технические теги сложности.
    text = re.sub(
        r"#FR_LEVEL_[123]",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Убираем отдельную ссылку в конце текста.
    # Ссылка на источник добавляется форматтером.
    text = re.sub(
        r"\n\s*https?://\S+\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Убираем лишние пробелы перед переносами строк.
    text = re.sub(
        r"[ \t]+\n",
        "\n",
        text,
    )

    # Убираем слишком большое количество пустых строк.
    text = re.sub(
        r"\n{3,}",
        "\n\n",
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


def has_ingredients_section(text: str) -> bool:
    """
    Проверяет, есть ли в публикации явный раздел
    с ингредиентами или составом.
    """
    lowered = text.lower()

    return any(
        marker in lowered
        for marker in INGREDIENT_SECTION_MARKERS
    )


def has_cooking_section(text: str) -> bool:
    """
    Проверяет, есть ли в публикации описание приготовления.
    """
    lowered = text.lower()

    if any(
        marker in lowered
        for marker in COOKING_SECTION_MARKERS
    ):
        return True

    # Ищем хотя бы два пронумерованных шага.
    numbered_steps = re.findall(
        r"(?m)^\s*\d+[\.\)]\s+\S+",
        text,
    )

    if len(numbered_steps) >= 2:
        return True

    # Допускаем текст с несколькими глаголами приготовления,
    # даже если отдельного заголовка нет.
    cooking_actions = (
        "добав",
        "нареж",
        "измельч",
        "смеш",
        "перемеш",
        "вар",
        "обжар",
        "жар",
        "выпек",
        "запек",
        "туш",
    )

    action_count = sum(
        1
        for action in cooking_actions
        if action in lowered
    )

    return action_count >= 2


def count_ingredient_lines(text: str) -> int:
    """
    Считает строки, похожие на элементы списка ингредиентов.

    Поддерживает форматы:
    - Картофель — 500 г
    - Картофель: 500 г
    - 500 г картофеля
    """
    ingredient_patterns = (
        # Картофель — 500 г
        r"(?im)^\s*[•\-–—]?\s*"
        r".{2,60}?\s*[—\-:]\s*"
        r"\d+(?:[.,]\d+)?\s*"
        r"(?:г|гр|кг|мл|л|шт|ст\.?\s*л|ч\.?\s*л)\b",

        # 500 г картофеля
        r"(?im)^\s*[•\-–—]?\s*"
        r"\d+(?:[.,]\d+)?\s*"
        r"(?:г|гр|кг|мл|л|шт|ст\.?\s*л|ч\.?\s*л)\b"
        r".{2,60}$",
    )

    matched_lines: set[str] = set()

    for pattern in ingredient_patterns:
        for match in re.findall(pattern, text):
            if isinstance(match, tuple):
                value = " ".join(match)
            else:
                value = match

            matched_lines.add(value.strip().lower())

    return len(matched_lines)


def has_recipe_structure(text: str) -> bool:
    """
    Проверяет наличие структуры полноценного рецепта.

    Для публикации требуются:
    1. ингредиенты;
    2. описание приготовления.
    """
    ingredients_found = (
        has_ingredients_section(text)
        or count_ingredient_lines(text) >= 2
    )

    cooking_found = has_cooking_section(text)

    return ingredients_found and cooking_found


def is_recipe_complete(text: str) -> bool:
    """
    Проверяет, достаточно ли рецепт наполнен
    для публикации в Food Radar.

    Главная цель — не публиковать короткие анонсы,
    ссылки и посты без ингредиентов.
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


def get_recipe_validation_reason(text: str) -> str:
    """
    Возвращает понятную причину,
    по которой рецепт не прошёл проверку.
    """
    if not text:
        return "пустой текст"

    clean_text = text.strip()

    if len(clean_text) < MIN_RECIPE_LENGTH:
        return (
            f"текст слишком короткий: "
            f"{len(clean_text)} < {MIN_RECIPE_LENGTH}"
        )

    meaningful_lines = count_meaningful_lines(clean_text)

    if meaningful_lines < MIN_RECIPE_LINES:
        return (
            f"слишком мало содержательных строк: "
            f"{meaningful_lines} < {MIN_RECIPE_LINES}"
        )

    food_markers = count_food_markers(clean_text)

    if food_markers < MIN_FOOD_MARKERS:
        return (
            f"слишком мало кулинарных признаков: "
            f"{food_markers} < {MIN_FOOD_MARKERS}"
        )

    if not has_ingredients_section(clean_text):
        ingredient_lines = count_ingredient_lines(clean_text)

        if ingredient_lines < 2:
            return "не найден раздел или список ингредиентов"

    if not has_cooking_section(clean_text):
        return "не найдено описание приготовления"

    return "неизвестная причина"


def publish_recipe(post: FoodPost) -> str:
    """
    Проверяет, обрабатывает и публикует один рецепт.

    Неполные публикации пропускаются.
    Дубликаты повторно не публикуются.
    """
    source_text = normalize_source_text(post.text)

    if not is_recipe_complete(source_text):
        reason = get_recipe_validation_reason(source_text)

        message = (
            "Пропуск: рецепт не содержит полного списка "
            "ингредиентов или описания приготовления."
        )

        print(
            "Recipe skipped: incomplete source text. "
            f"message_id={post.message_id}, "
            f"length={len(source_text)}, "
            f"lines={count_meaningful_lines(source_text)}, "
            f"markers={count_food_markers(source_text)}, "
            f"ingredient_lines={count_ingredient_lines(source_text)}, "
            f"reason={reason}"
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
