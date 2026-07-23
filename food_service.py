from __future__ import annotations

import re

from food_post import process_recipe
from food_telegram import send_food_message
from sources.food_source import FoodPost


MIN_RECIPE_LENGTH = 180
MIN_RECIPE_LINES = 2
MIN_FOOD_MARKERS = 1


FOOD_MARKERS = (
    "ингредиент",
    "состав",
    "продукт",
    "понадоб",
    "потребуется",
    "приготов",
    "рецепт",
    "добав",
    "нареж",
    "измельч",
    "смеш",
    "перемеш",
    "взб",
    "вар",
    "отвар",
    "обжар",
    "жар",
    "выпек",
    "запек",
    "туш",
    "маринов",
    "тесто",
    "начинк",
    "соус",
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
    "стакан",
    "ложк",
)


INGREDIENT_SECTION_MARKERS = (
    "ингредиенты",
    "ингредиент",
    "состав",
    "состав блюда",
    "продукты",
    "список продуктов",
    "необходимые продукты",
    "необходимые ингредиенты",
    "нам понадобится",
    "нам потребуется",
    "вам понадобится",
    "вам потребуется",
    "понадобится",
    "потребуется",
    "что понадобится",
    "что потребуется",
    "для рецепта",
    "для приготовления",
    "для теста",
    "для начинки",
    "для крема",
    "для соуса",
    "для маринада",
    "для украшения",
)


COOKING_SECTION_MARKERS = (
    "приготовление",
    "как приготовить",
    "способ приготовления",
    "процесс приготовления",
    "пошаговый рецепт",
    "пошаговое приготовление",
    "инструкция",
    "готовим",
    "начинаем готовить",
    "ход приготовления",
    "этапы приготовления",
)


COOKING_ACTIONS = (
    "добав",
    "нареж",
    "пореж",
    "измельч",
    "натр",
    "смеш",
    "перемеш",
    "взб",
    "влей",
    "налей",
    "залей",
    "всып",
    "полож",
    "вылож",
    "вар",
    "отвар",
    "обжар",
    "жар",
    "выпек",
    "запек",
    "туш",
    "маринов",
    "разогрей",
    "охлад",
    "остав",
    "посып",
    "смаж",
    "очист",
    "промой",
)


UNITS_PATTERN = (
    r"(?:"
    r"г|гр|грамм(?:а|ов)?|"
    r"кг|килограмм(?:а|ов)?|"
    r"мл|миллилитр(?:а|ов)?|"
    r"л|литр(?:а|ов)?|"
    r"шт|штук(?:а|и)?|"
    r"ст\.?\s*л\.?|столов\w*\s+лож\w*|"
    r"ч\.?\s*л\.?|чай\w*\s+лож\w*|"
    r"стакан(?:а|ов)?|"
    r"чашк(?:а|и|ек)|"
    r"щепотк(?:а|и)?|"
    r"зубчик(?:а|ов)?|"
    r"веточк(?:а|и|ек)|"
    r"пучок|пучка|пучков|"
    r"банка|банки|банок|"
    r"упаковк(?:а|и|ок)|"
    r"кусоч(?:ек|ка|ков)"
    r")"
)


def normalize_source_text(text: str) -> str:
    """
    Очищает исходный текст перед проверкой.
    Полезное содержимое рецепта не обрезается.
    """
    if not text:
        return ""

    text = text.strip()

    text = text.replace("\u200b", "")
    text = text.replace("\ufeff", "")
    text = text.replace("\xa0", " ")
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Превращаем распространённые HTML-переносы в обычные.
    text = re.sub(
        r"(?i)<br\s*/?>",
        "\n",
        text,
    )

    # Удаляем оставшиеся HTML-теги.
    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    # Удаляем технические теги сложности.
    text = re.sub(
        r"#FR_LEVEL_[123]",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Убираем отдельную ссылку в конце текста.
    text = re.sub(
        r"\n\s*https?://\S+\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Убираем лишние пробелы перед переносами.
    text = re.sub(
        r"[ \t]+\n",
        "\n",
        text,
    )

    # Схлопываем повторяющиеся пробелы внутри строк.
    text = re.sub(
        r"[ \t]{2,}",
        " ",
        text,
    )

    # Ограничиваем количество пустых строк.
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


def count_meaningful_lines(text: str) -> int:
    """
    Считает строки с полезным содержимым.
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
    Считает уникальные кулинарные признаки.
    """
    lowered = text.lower()

    return sum(
        1
        for marker in FOOD_MARKERS
        if marker in lowered
    )


def has_ingredients_section(text: str) -> bool:
    """
    Ищет явный заголовок или обозначение ингредиентов.
    Поддерживает эмодзи и разные знаки после заголовка.
    """
    lowered = text.lower()

    return any(
        marker in lowered
        for marker in INGREDIENT_SECTION_MARKERS
    )


def has_cooking_section(text: str) -> bool:
    """
    Проверяет наличие описания приготовления.
    """
    lowered = text.lower()

    if any(
        marker in lowered
        for marker in COOKING_SECTION_MARKERS
    ):
        return True

    # Пронумерованные шаги:
    # 1. Нарежьте...
    # 2) Добавьте...
    numbered_steps = re.findall(
        r"(?m)^\s*(?:шаг\s*)?\d+\s*[\.\):\-]\s+\S+",
        text,
        flags=re.IGNORECASE,
    )

    if len(numbered_steps) >= 2:
        return True

    action_count = sum(
        1
        for action in COOKING_ACTIONS
        if action in lowered
    )

    return action_count >= 2


def is_likely_ingredient_line(line: str) -> bool:
    """
    Определяет, похожа ли отдельная строка на ингредиент.
    """
    clean_line = line.strip()

    if not clean_line:
        return False

    # Убираем маркеры списков и эмодзи в начале.
    clean_line = re.sub(
        r"^[\s•●▪▫◦·*✅☑️✔️🔸🔹🥄🍴📌➖\-–—]+",
        "",
        clean_line,
    ).strip()

    if len(clean_line) < 3 or len(clean_line) > 160:
        return False

    lowered = clean_line.lower()

    # Исключаем явные инструкции приготовления.
    action_matches = sum(
        1
        for action in COOKING_ACTIONS
        if action in lowered
    )

    if action_matches >= 2:
        return False

    number_pattern = (
        r"(?:"
        r"\d+(?:[.,]\d+)?|"
        r"\d+\s*/\s*\d+|"
        r"[¼½¾⅓⅔⅛]"
        r")"
    )

    # Картофель — 500 г
    # Мука: 2 стакана
    if re.search(
        rf"{number_pattern}\s*{UNITS_PATTERN}\b",
        lowered,
        flags=re.IGNORECASE,
    ):
        return True

    # 2 яйца
    # 3 помидора
    if re.search(
        r"^\s*\d+(?:[.,]\d+)?\s+"
        r"[а-яёa-z][а-яёa-z\-]{2,}",
        lowered,
        flags=re.IGNORECASE,
    ):
        return True

    # Мука 300 г
    # Сахар 2 ст. л.
    if re.search(
        rf"[а-яёa-z][а-яёa-z\- ]{{2,}}\s+"
        rf"{number_pattern}\s*{UNITS_PATTERN}\b",
        lowered,
        flags=re.IGNORECASE,
    ):
        return True

    # Соль по вкусу
    # Перец по вкусу
    if re.search(
        r"\b(?:соль|перец|специи|зелень|сахар)"
        r"\s+(?:по вкусу|по желанию)\b",
        lowered,
    ):
        return True

    # Масло для жарки
    # Зелень для подачи
    if re.search(
        r"\b(?:масло|зелень|соус|сметана)"
        r"\s+для\s+(?:жарки|подачи|смазывания)\b",
        lowered,
    ):
        return True

    return False


def count_compact_ingredients(text: str) -> int:
    """
    Распознаёт компактные списки после заголовка:

    Ингредиенты: мука 200 г, яйца 2 шт.,
    сахар 100 г, масло 50 г.
    """
    lowered = text.lower()

    marker_position = -1
    marker_length = 0

    for marker in INGREDIENT_SECTION_MARKERS:
        position = lowered.find(marker)

        if position != -1:
            marker_position = position
            marker_length = len(marker)
            break

    if marker_position == -1:
        return 0

    fragment = text[
        marker_position + marker_length:
        marker_position + marker_length + 1000
    ]

    # Не захватываем раздел приготовления.
    fragment_lowered = fragment.lower()

    stop_positions = [
        fragment_lowered.find(marker)
        for marker in COOKING_SECTION_MARKERS
        if fragment_lowered.find(marker) != -1
    ]

    if stop_positions:
        fragment = fragment[:min(stop_positions)]

    parts = re.split(
        r"[,;\n•●▪▫◦]+",
        fragment,
    )

    return sum(
        1
        for part in parts
        if is_likely_ingredient_line(part)
    )


def count_ingredient_lines(text: str) -> int:
    """
    Считает ингредиенты в построчных и компактных списках.
    """
    matched_lines: set[str] = set()

    for line in text.splitlines():
        clean_line = line.strip().lower()

        if is_likely_ingredient_line(clean_line):
            matched_lines.add(clean_line)

    line_count = len(matched_lines)
    compact_count = count_compact_ingredients(text)

    return max(line_count, compact_count)


def has_recipe_structure(text: str) -> bool:
    """
    Для публикации нужны ингредиенты и приготовление.
    """
    ingredient_lines = count_ingredient_lines(text)

    ingredients_found = (
        ingredient_lines >= 2
        or (
            has_ingredients_section(text)
            and ingredient_lines >= 1
        )
    )

    cooking_found = has_cooking_section(text)

    return ingredients_found and cooking_found


def is_recipe_complete(text: str) -> bool:
    """
    Проверяет полноту рецепта.
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
    Возвращает точную причину отказа.
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

    ingredient_lines = count_ingredient_lines(clean_text)

    if ingredient_lines < 2:
        return (
            "не найден полноценный список ингредиентов: "
            f"{ingredient_lines} < 2"
        )

    if not has_cooking_section(clean_text):
        return "не найдено описание приготовления"

    return "неизвестная причина"


def publish_recipe(post: FoodPost) -> str:
    """
    Проверяет, обрабатывает и публикует рецепт.

    При успешной публикации возвращает строку:
    Рецепт опубликован: TELEGRAM_MESSAGE_ID

    По этой строке food_runner.py понимает,
    что рецепт можно переслать в News Radar.
    """
    source_text = normalize_source_text(
        post.text
    )

    print(
        "\n===== RECIPE DEBUG START =====\n"
        f"message_id={post.message_id}\n"
        f"{source_text[:2500]}\n"
        "===== RECIPE DEBUG END =====\n"
    )

    if not is_recipe_complete(source_text):
        reason = get_recipe_validation_reason(
            source_text
        )

        message = (
            "Пропуск: рецепт не содержит полного "
            "списка ингредиентов или описания "
            "приготовления."
        )

        print(
            "Recipe skipped: incomplete source text. "
            f"message_id={post.message_id}, "
            f"length={len(source_text)}, "
            f"lines={count_meaningful_lines(source_text)}, "
            f"markers={count_food_markers(source_text)}, "
            f"ingredient_lines="
            f"{count_ingredient_lines(source_text)}, "
            f"ingredients_section="
            f"{has_ingredients_section(source_text)}, "
            f"cooking_section="
            f"{has_cooking_section(source_text)}, "
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
        f"telegram_message_id="
        f"{published_message_id}"
    )

    return (
        "Рецепт опубликован: "
        f"{published_message_id}"
    )
