from __future__ import annotations

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


def parse_eda(html: str) -> str:
    """
    Извлекает текст рецепта из eda.ru.
    """

    soup = BeautifulSoup(
        html,
        "lxml",
    )

    article = soup.find("article")

    if article:
        return clean_text(article.get_text("\n"))

    return ""


def parse_1000menu(html: str) -> str:
    """
    Пока заглушка.
    """

    return ""


import json


def parse_povar(html: str) -> str:
    """
    Извлекает рецепт с povar.ru.

    Сначала используется JSON-LD (Schema.org Recipe),
    затем — запасной вариант через HTML.
    """
    soup = BeautifulSoup(html, "lxml")

    # ---------- JSON-LD ----------
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue

        objects = data if isinstance(data, list) else [data]

        for obj in objects:
            if not isinstance(obj, dict):
                continue

            if obj.get("@type") != "Recipe":
                continue

            ingredients = obj.get("recipeIngredient", [])

            instructions = obj.get("recipeInstructions", [])

            steps = []

            for item in instructions:
                if isinstance(item, dict):
                    text = item.get("text")
                    if text:
                        steps.append(text)
                elif isinstance(item, str):
                    steps.append(item)

            parts = []

            if ingredients:
                parts.append("Ингредиенты")
                parts.extend(ingredients)

            if steps:
                parts.append("")
                parts.append("Приготовление")

                for i, step in enumerate(steps, 1):
                    parts.append(f"{i}. {step}")

            if parts:
                return clean_text("\n".join(parts))

    # ---------- HTML fallback ----------
    article = soup.find("article")

    if article:
        return clean_text(article.get_text("\n"))

    return ""


def parse_iamcook(html: str) -> str:
    """
    Пока заглушка.
    """

    return ""
