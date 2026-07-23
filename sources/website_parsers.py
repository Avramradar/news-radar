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


def parse_povar(html: str) -> str:
    """
    Пока заглушка.
    """

    return ""


def parse_iamcook(html: str) -> str:
    """
    Пока заглушка.
    """

    return ""
