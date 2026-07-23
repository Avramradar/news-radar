from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

import requests

from .base_source import BaseSource
from .food_source import FoodPost
from .website_parsers import (
    parse_1000menu,
    parse_eda,
    parse_iamcook,
    parse_povar,
)


class WebsiteSource(BaseSource):
    """
    Загружает рецепты с кулинарных сайтов.
    """

    def __init__(self) -> None:
        self.timeout = 20

    def load_sources(self) -> list[str]:
        config = Path("sources.json")

        if not config.exists():
            return []

        with config.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        return data.get("websites", [])

    def download(self, url: str) -> str:
        response = requests.get(
            url,
            timeout=self.timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 FoodRadarBot/1.0"
                )
            },
        )

        response.raise_for_status()

        return response.text

    def parse(self, url: str, html: str) -> str:
        host = urlparse(url).netloc.lower()

        if "eda.ru" in host:
            return parse_eda(html)

        if "1000.menu" in host:
            return parse_1000menu(html)

        if "povar.ru" in host:
            return parse_povar(html)

        if "iamcook.ru" in host:
            return parse_iamcook(html)

        return ""

    def fetch(self) -> list[FoodPost]:

        posts: list[FoodPost] = []

        for url in self.load_sources():

            try:
                html = self.download(url)

                text = self.parse(url, html)

                if not text:
                    continue

                posts.append(
                    FoodPost(
                        text=text,
                        message_id=0,
                        source_url=url,
                        image_url="",
                    )
                )

                print(f"Website OK: {url}")

            except Exception as error:
                print(f"Website ERROR: {url}: {error}")

        return posts
