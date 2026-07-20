"""
Food Radar Storage

Хранение рецептов и состояния публикаций.
Используется каналом Food Radar и News Radar.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


STORAGE_FILE = Path("food_state.json")


def load_storage() -> dict[str, Any]:
    """Загружает сохранённые данные из food_state.json."""
    if not STORAGE_FILE.exists():
        return {
            "recipes": [],
            "published_to_news": [],
        }

    try:
        with STORAGE_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {
            "recipes": [],
            "published_to_news": [],
        }

    if not isinstance(data, dict):
        return {
            "recipes": [],
            "published_to_news": [],
        }

    data.setdefault("recipes", [])
    data.setdefault("published_to_news", [])

    return data


def save_storage(data: dict[str, Any]) -> None:
    """Сохраняет данные в food_state.json."""
    with STORAGE_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )
