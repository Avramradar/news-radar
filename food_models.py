from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Recipe:
    title: str
    difficulty: int
    category: str
    source_url: str
    image_url: str
    content: str
    message_id: int | None = None
    published: bool = False


@dataclass
class FoodPost:
    text: str
    message_id: int
    source_url: str
    image_url: str = ""
