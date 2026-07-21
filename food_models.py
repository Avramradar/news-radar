from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FoodPost:
    text: str
    message_id: int
    source_url: str
    image_url: str = ""
