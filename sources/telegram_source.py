
from __future__ import annotations

import json
from pathlib import Path


class TelegramSource:
    """
    Загружает список Telegram-источников
    из файла sources.json.
    """

    def __init__(self) -> None:
        self.sources = self.load_sources()

    def load_sources(self) -> list[str]:
        config = Path("sources.json")

        if not config.exists():
            return []

        with config.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        return data.get("telegram", [])

    def fetch(self):
        """
        Пока просто выводит список каналов.

        На следующем этапе вместо print
        будет подключение к Telegram.
        """
        for source in self.sources:
            print(source)

        return []
