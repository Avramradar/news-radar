from __future__ import annotations

from urllib.parse import urlparse

import requests

from sources.website_parsers import (
    parse_1000menu,
    parse_eda,
    parse_gastronom,
    parse_iamcook,
    parse_povar,
)


class RecipeLoader:
    """
    Загружает полную страницу рецепта
    и извлекает полный текст.
    """

    def __init__(self) -> None:
        self.timeout = 20

    def load(self, url: str) -> str:
        response = requests.get(
            url,
            timeout=self.timeout,
            headers={
                "User-Agent": "FoodRadarBot/1.0"
            },
        )

        response.raise_for_status()

        html = response.text

        host = urlparse(url).netloc.lower()

        if "eda.ru" in host:
            return parse_eda(html)

        if "1000.menu" in host:
            return parse_1000menu(html)

        if "povar.ru" in host:
            return parse_povar(html)

        if "gastronom.ru" in host:
            return parse_gastronom(html)

        if "iamcook.ru" in host:
            return parse_iamcook(html)

        return ""
