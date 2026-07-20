from __future__ import annotations

from abc import ABC, abstractmethod


class BaseSource(ABC):
    """
    Базовый класс для всех источников данных.
    """

    @abstractmethod
    def fetch(self):
        """
        Возвращает новые записи из источника.
        """
        raise NotImplementedError

