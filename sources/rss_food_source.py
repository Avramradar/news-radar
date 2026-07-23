from __future__ import annotations

import hashlib
import html
import re
from pathlib import Path

import feedparser

from food_models import FoodPost
from recipe_loader import RecipeLoader
from sources.base_source import BaseSource


class RssFoodSource(BaseSource):
    """
    Получает публикации из кулинарных RSS-лент.

    RSS используется для обнаружения новых рецептов.
    После получения ссылки выполняется попытка загрузить
    полный текст рецепта со страницы сайта.

    Если полную страницу получить не удалось,
    используется заголовок и краткое описание из RSS.
    """

    SOURCE_FILE = Path("food_sources.txt")
    ENTRIES_PER_FEED = 2

    def fetch(self) -> list[FoodPost]:
        """
        Читает адреса RSS-лент, получает свежие записи
        и возвращает их в виде списка FoodPost.
        """
        feed_urls = self._load_feed_urls()

        if not feed_urls:
            return []

        posts: list[FoodPost] = []
        loader = RecipeLoader()

        for feed_url in feed_urls:
            feed = self._load_feed(feed_url)

            if feed is None:
                continue

            entries = getattr(feed, "entries", [])

            if not entries:
                print(f"В RSS нет записей: {feed_url}")
                continue

            for entry in entries[: self.ENTRIES_PER_FEED]:
                post = self._build_post(
                    entry=entry,
                    loader=loader,
                )

                if post is not None:
                    posts.append(post)

        print(
            "RSS-обработка завершена. "
            f"Получено публикаций: {len(posts)}"
        )

        return posts

    def _load_feed_urls(self) -> list[str]:
        """
        Загружает список RSS-адресов из food_sources.txt.

        Пустые строки и комментарии, начинающиеся с #,
        игнорируются.
        """
        if not self.SOURCE_FILE.exists():
            print("Файл food_sources.txt не найден.")
            return []

        urls_text = self.SOURCE_FILE.read_text(
            encoding="utf-8"
        ).strip()

        if not urls_text:
            print("Файл food_sources.txt пуст.")
            return []

        feed_urls = [
            line.strip()
            for line in urls_text.splitlines()
            if line.strip()
            and not line.strip().startswith("#")
        ]

        if not feed_urls:
            print(
                "В файле food_sources.txt "
                "нет доступных RSS-адресов."
            )

        return feed_urls

    @staticmethod
    def _load_feed(feed_url: str):
        """
        Загружает одну RSS-ленту.

        Ошибка одной ленты не останавливает
        обработку остальных источников.
        """
        try:
            print(f"Проверка RSS: {feed_url}")
            feed = feedparser.parse(feed_url)
        except Exception as error:
            print(f"Ошибка RSS {feed_url}: {error}")
            return None

        if getattr(feed, "bozo", False):
            error = getattr(
                feed,
                "bozo_exception",
                "",
            )

            print(
                f"Предупреждение RSS {feed_url}: "
                f"{error}"
            )

        return feed

    def _build_post(
        self,
        entry,
        loader: RecipeLoader,
    ) -> FoodPost | None:
        """
        Создаёт FoodPost из одной записи RSS.

        Сначала пытается получить полный рецепт
        по ссылке. При ошибке использует RSS-анонс.
        """
        title = str(
            entry.get("title", "")
        ).strip()

        source_url = str(
            entry.get("link", "")
        ).strip()

        if not title or not source_url:
            print(
                "RSS-запись пропущена: "
                "нет заголовка или ссылки."
            )
            return None

        raw_summary = str(
            entry.get(
                "summary",
                entry.get("description", ""),
            )
        )

        summary = self._clean_html(raw_summary)
        image_url = self._extract_image(entry)
        message_id = self._make_message_id(source_url)

        full_text = self._load_full_recipe(
            loader=loader,
            source_url=source_url,
        )

        if full_text:
            text = self._combine_title_and_text(
                title=title,
                body=full_text,
            )

            print(
                "Получен полный рецепт: "
                f"{source_url}"
            )
        else:
            text = self._combine_title_and_text(
                title=title,
                body=summary,
            )

            print(
                "Использован RSS-анонс: "
                f"{source_url}"
            )

        return FoodPost(
            text=text,
            message_id=message_id,
            source_url=source_url,
            image_url=image_url,
        )

    @staticmethod
    def _load_full_recipe(
        loader: RecipeLoader,
        source_url: str,
    ) -> str:
        """
        Пытается загрузить полный текст рецепта.

        Любая ошибка обрабатывается локально,
        чтобы одна страница не остановила весь запуск.
        """
        try:
            return loader.load(source_url).strip()
        except Exception as error:
            print(
                "Не удалось загрузить полную страницу "
                f"{source_url}: {error}"
            )

            return ""

    @staticmethod
    def _combine_title_and_text(
        title: str,
        body: str,
    ) -> str:
        """
        Объединяет заголовок и содержимое,
        не дублируя заголовок страницы.
        """
        clean_title = title.strip()
        clean_body = body.strip()

        if not clean_body:
            return clean_title

        normalized_title = re.sub(
            r"\s+",
            " ",
            clean_title,
        ).casefold()

        normalized_body_start = re.sub(
            r"\s+",
            " ",
            clean_body[: len(clean_title) + 30],
        ).casefold()

        if (
            normalized_title
            and normalized_body_start.startswith(
                normalized_title
            )
        ):
            return clean_body

        return f"{clean_title}\n\n{clean_body}"

    @staticmethod
    def _clean_html(value: str) -> str:
        """
        Удаляет HTML-разметку из RSS-анонса
        и нормализует пробелы.
        """
        clean = re.sub(
            r"<[^>]+>",
            " ",
            value,
        )

        clean = html.unescape(clean)

        clean = re.sub(
            r"\s+",
            " ",
            clean,
        )

        return clean.strip()

    @staticmethod
    def _make_message_id(source_url: str) -> int:
        """
        Создаёт стабильный числовой идентификатор
        на основе ссылки на исходную публикацию.
        """
        digest = hashlib.sha256(
            source_url.encode("utf-8")
        ).hexdigest()

        return int(digest[:12], 16)

    @staticmethod
    def _extract_image(entry) -> str:
        """
        Извлекает изображение из стандартных полей RSS.

        Проверяются:
        - media_content;
        - media_thumbnail;
        - enclosures;
        - тег img внутри summary/description.
        """
        media_content = entry.get(
            "media_content",
            [],
        )

        if media_content:
            image_url = media_content[0].get(
                "url",
                "",
            )

            if image_url:
                return str(image_url)

        media_thumbnail = entry.get(
            "media_thumbnail",
            [],
        )

        if media_thumbnail:
            image_url = media_thumbnail[0].get(
                "url",
                "",
            )

            if image_url:
                return str(image_url)

        enclosures = entry.get(
            "enclosures",
            [],
        )

        for enclosure in enclosures:
            enclosure_type = str(
                enclosure.get("type", "")
            )

            if enclosure_type.startswith("image/"):
                return str(
                    enclosure.get("href", "")
                )

        raw_summary = str(
            entry.get(
                "summary",
                entry.get("description", ""),
            )
        )

        match = re.search(
            r'<img[^>]+src=["\']([^"\']+)["\']',
            raw_summary,
            flags=re.IGNORECASE,
        )

        if match:
            return html.unescape(
                match.group(1)
            )

        return ""
