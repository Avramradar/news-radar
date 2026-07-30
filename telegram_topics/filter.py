from __future__ import annotations

from pathlib import Path

from parser import TelegramPost


class MilitaryFilter:
    """
    Фильтр сообщений по ключевым словам и blacklist.
    """

    def __init__(
        self,
        topic_dir: str = "telegram_topics/military",
    ) -> None:

        topic = Path(topic_dir)

        self.keywords = self._load(
            topic / "keywords.txt"
        )

        self.blacklist = self._load(
            topic / "blacklist.txt"
        )

    @staticmethod
    def _load(path: Path) -> set[str]:
        if not path.exists():
            return set()

        result = set()

        for line in path.read_text(
            encoding="utf-8"
        ).splitlines():

            line = line.strip().lower()

            if not line:
                continue

            if line.startswith("#"):
                continue

            result.add(line)

        return result

    def check(
        self,
        post: TelegramPost,
    ) -> bool:

        text = post.text.lower()

        for word in self.blacklist:
            if word in text:
                return False

        for word in self.keywords:
            if word in text:
                return True

        return False
