from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup


def clean_text(text: str) -> str:
    """
    Удаляет лишние пробелы и пустые строки.
    """
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    return "\n".join(lines)


def _is_recipe_type(value: Any) -> bool:
    """
    Проверяет значение поля @type.
    """
    if isinstance(value, str):
        return value.casefold() == "recipe"

    if isinstance(value, list):
        return any(
            isinstance(item, str)
            and item.casefold() == "recipe"
            for item in value
        )

    return False


def _find_recipe_objects(value: Any) -> list[dict]:
    """
    Рекурсивно ищет объекты Schema.org Recipe.

    Поддерживает:
    - обычный объект;
    - список объектов;
    - контейнер @graph;
    - вложенные структуры.
    """
    found: list[dict] = []

    if isinstance(value, dict):
        if _is_recipe_type(value.get("@type")):
            found.append(value)

        for nested_value in value.values():
            found.extend(
                _find_recipe_objects(nested_value)
            )

    elif isinstance(value, list):
        for item in value:
            found.extend(
                _find_recipe_objects(item)
            )

    return found


def _extract_instruction_text(value: Any) -> list[str]:
    """
    Извлекает шаги приготовления из разных вариантов
    recipeInstructions.
    """
    steps: list[str] = []

    if isinstance(value, str):
        clean_value = clean_text(value)

        if clean_value:
            steps.append(clean_value)

        return steps

    if isinstance(value, list):
        for item in value:
            steps.extend(
                _extract_instruction_text(item)
            )

        return steps

    if not isinstance(value, dict):
        return steps

    text = value.get("text")

    if isinstance(text, str):
        clean_value = clean_text(text)

        if clean_value:
            steps.append(clean_value)

    # HowToSection часто содержит шаги внутри itemListElement.
    nested_items = value.get("itemListElement")

    if nested_items:
        steps.extend(
            _extract_instruction_text(nested_items)
        )

    # Иногда инструкции вложены в steps.
    nested_steps = value.get("steps")

    if nested_steps:
        steps.extend(
            _extract_instruction_text(nested_steps)
        )

    return steps


def _build_recipe_text(recipe: dict) -> str:
    """
    Создаёт единый текст из объекта Schema.org Recipe.
    """
    raw_ingredients = recipe.get(
        "recipeIngredient",
        [],
    )

    if isinstance(raw_ingredients, str):
        ingredients = [
            line.strip()
            for line in raw_ingredients.splitlines()
            if line.strip()
        ]
    elif isinstance(raw_ingredients, list):
        ingredients = [
            clean_text(str(item))
            for item in raw_ingredients
            if str(item).strip()
        ]
    else:
        ingredients = []

    steps = _extract_instruction_text(
        recipe.get("recipeInstructions", [])
    )

    # Без ингредиентов и приготовления это не полный рецепт.
    if not ingredients or not steps:
        return ""

    parts: list[str] = [
        "Ингредиенты",
    ]

    for ingredient in ingredients:
        parts.append(f"- {ingredient}")

    parts.extend(
        [
            "",
            "Приготовление",
        ]
    )

    for number, step in enumerate(steps, 1):
        parts.append(f"{number}. {step}")

    return clean_text("\n".join(parts))


def parse_json_ld_recipe(html: str) -> str:
    """
    Ищет полный рецепт в JSON-LD страницы.
    """
    soup = BeautifulSoup(
        html,
        "lxml",
    )

    scripts = soup.find_all(
        "script",
        type="application/ld+json",
    )

    for script in scripts:
        raw_json = script.string

        if not raw_json:
            raw_json = script.get_text(
                strip=True
            )

        if not raw_json:
            continue

        try:
            data = json.loads(raw_json)
        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ):
            continue

        for recipe in _find_recipe_objects(data):
            recipe_text = _build_recipe_text(
                recipe
            )

            if recipe_text:
                return recipe_text

    return ""


def parse_eda(html: str) -> str:
    """
    Извлекает текст рецепта из eda.ru.
    """
    recipe_text = parse_json_ld_recipe(html)

    if recipe_text:
        return recipe_text

    soup = BeautifulSoup(
        html,
        "lxml",
    )

    article = soup.find("article")

    if article:
        return clean_text(
            article.get_text("\n")
        )

    return ""


def parse_1000menu(html: str) -> str:
    """
    Извлекает рецепт из 1000.menu.
    """
    return parse_json_ld_recipe(html)

def parse_say7(html: str) -> str:
    """
    Извлекает рецепт с say7.info.

    Сначала пытается использовать Schema.org Recipe.
    """
    return parse_json_ld_recipe(html)

def parse_vpuzo(html: str) -> str:
    """
    Извлекает полный рецепт с vpuzo.com.

    Сайт использует Schema.org Microdata прямо в HTML:
    - itemprop="recipeIngredient";
    - itemprop="recipeInstructions".
    """
    soup = BeautifulSoup(
        html,
        "lxml",
    )

    recipe = soup.find(
        attrs={
            "itemtype": re.compile(
                r"schema\.org/Recipe",
                re.IGNORECASE,
            )
        }
    )

    if recipe is None:
        recipe = soup.select_one(
            "section.recipe.block"
        )

    if recipe is None:
        return ""

    ingredients: list[str] = []

    for node in recipe.find_all(
        attrs={"itemprop": "recipeIngredient"}
    ):
        if node.name == "meta":
            value = str(
                node.get("content", "")
            )
        else:
            value = str(
                node.get("content", "")
            )

            if not value:
                value = node.get_text(
                    " ",
                    strip=True,
                )

        value = clean_text(value)

        if value and value not in ingredients:
            ingredients.append(value)

    steps: list[str] = []

    instruction_nodes = recipe.find_all(
        attrs={"itemprop": "recipeInstructions"}
    )

    for node in instruction_nodes:
        if node.name == "meta":
            value = str(
                node.get("content", "")
            )

            value = clean_text(value)

            if value and value not in steps:
                steps.append(value)

            continue

        child_steps = node.find_all(
            ["li", "p"],
        )

        if child_steps:
            for child in child_steps:
                value = clean_text(
                    child.get_text(
                        " ",
                        strip=True,
                    )
                )

                if value and value not in steps:
                    steps.append(value)
        else:
            value = clean_text(
                node.get_text(
                    " ",
                    strip=True,
                )
            )

            if value and value not in steps:
                steps.append(value)

    # Запасной поиск по классам, если itemprop отсутствует.
    if not steps:
        step_selectors = (
            ".recipe-steps li",
            ".recipe-instructions li",
            ".recipe-preparation li",
            ".instructions li",
            ".steps li",
            "[class*='step'] li",
        )

        for selector in step_selectors:
            for node in recipe.select(selector):
                value = clean_text(
                    node.get_text(
                        " ",
                        strip=True,
                    )
                )

                if value and value not in steps:
                    steps.append(value)

    # Последний запасной вариант:
    # ищем заголовок «Приготовление» внутри блока рецепта.
    if not steps:
        heading = recipe.find(
            string=re.compile(
                r"^\s*(?:приготовление|"
                r"способ приготовления|"
                r"как приготовить)\s*:?\s*$",
                re.IGNORECASE,
            )
        )

        if heading:
            container = heading.parent

            if container:
                sibling = container.find_next_sibling()

                while sibling is not None:
                    sibling_text = clean_text(
                        sibling.get_text(
                            " ",
                            strip=True,
                        )
                    )

                    if re.search(
                        r"^(?:комментарии|"
                        r"похожие рецепты|"
                        r"советы)\b",
                        sibling_text,
                        re.IGNORECASE,
                    ):
                        break

                    if sibling_text:
                        child_steps = sibling.find_all(
                            ["li", "p"],
                        )

                        if child_steps:
                            for child in child_steps:
                                value = clean_text(
                                    child.get_text(
                                        " ",
                                        strip=True,
                                    )
                                )

                                if (
                                    value
                                    and value not in steps
                                ):
                                    steps.append(value)
                        elif sibling_text not in steps:
                            steps.append(sibling_text)

                    sibling = sibling.find_next_sibling()

    if not ingredients or not steps:
        print(
            "VPUZO: неполный рецепт. "
            f"ingredients={len(ingredients)}, "
            f"steps={len(steps)}"
        )
        return ""

    parts: list[str] = [
        "Ингредиенты",
    ]

    for ingredient in ingredients:
        parts.append(
            f"- {ingredient}"
        )

    parts.extend(
        [
            "",
            "Приготовление",
        ]
    )

    for number, step in enumerate(
        steps,
        1,
    ):
        # Не добавляем вторую нумерацию, если она уже есть.
        if re.match(
            r"^\s*(?:шаг\s*)?\d+[\.\):\-]",
            step,
            re.IGNORECASE,
        ):
            parts.append(step)
        else:
            parts.append(
                f"{number}. {step}"
            )

    return clean_text(
        "\n".join(parts)
    )


def parse_povar(html: str) -> str:
    """
    Извлекает рецепт с povar.ru.
    """
    recipe_text = parse_json_ld_recipe(html)

    if recipe_text:
        return recipe_text

    # Запасной вариант оставляем только для povar.ru,
    # где он уже показал рабочий результат.
    soup = BeautifulSoup(
        html,
        "lxml",
    )

    article = soup.find("article")

    if article:
        return clean_text(
            article.get_text("\n")
        )

    return ""


def parse_gastronom(html: str) -> str:
    """
    Извлекает только полноценный рецепт с gastronom.ru.

    Обычные статьи и рекламные материалы без Schema.org Recipe
    намеренно не принимаются.
    """
    return parse_json_ld_recipe(html)


def parse_iamcook(html: str) -> str:
    """
    Извлекает рецепт с iamcook.ru.
    """
    return parse_json_ld_recipe(html)
