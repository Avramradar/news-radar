from __future__ import annotations

from .base_source import BaseSource


class FoodSource(BaseSource):
    """
    Источник рецептов Food Radar.
    """

    def fetch(self):
        """
        Пока источник ничего не возвращает.
        Реальная логика будет добавлена позже.
        """
        return []
