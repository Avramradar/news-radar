from __future__ import annotations

import hashlib
import html
import os
import re

import feedparser

from .base_source import BaseSource
from .food_source import FoodPost


class RssFoodSource(BaseSource):
    """Получает публикации из кулинарных RSS-лент."""

    def fetch(self) -> list[FoodPost]:
        urls_text = os.getenv("FOOD_RSS_URLS", "").strip()

        if not urls_text:
            return []

        feed_urls = [
            url.strip()
            for url in urls_text.split(",")
            if url.strip()
        ]

        posts: list[FoodPost] = []

       
