from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Recipe:
    title: str
    difficulty: int
    category: str
    source_url: str
    image_url: str
    message_id: int | None = None
    published: bool = False
