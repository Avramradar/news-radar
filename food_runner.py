from __future__ import annotations

from food_service import publish_recipe
from food_to_news import copy_message
from sources.rss_food_source import RssFoodSource
from sources.telegram_source import TelegramSource
from sources.youtube_source import YouTubeSource


def extract_published_message_id(
    result: object,
) -> int | None:
    """
    Извлекает Telegram message_id из результата:

    Рецепт опубликован: 123
    """
    result_text = str(result).strip()

    if not result_text.startswith(
        "Рецепт опубликован"
    ):
        return None

    try:
        return int(
            result_text.rsplit(
                ":",
                1,
            )[1].strip()
        )
    except (
        IndexError,
        TypeError,
        ValueError,
    ):
        print(
            "Не удалось получить message_id "
            "из результата публикации:",
            result_text,
        )
        return None


def main() -> None:
    """
    Запускает все подключённые источники Food Radar.

    Ошибка одного источника не останавливает
    обработку остальных источников.
    """
    sources = [
        RssFoodSource(),
        TelegramSource(),
        YouTubeSource(),
    ]

    all_posts = []

    for source in sources:
        source_name = (
            source.__class__.__name__
        )

        try:
            print(
                f"Запуск источника: "
                f"{source_name}"
            )

            posts = source.fetch()

            all_posts.extend(posts)

            print(
                f"Источник {source_name} "
                f"завершён. Получено: "
                f"{len(posts)}"
            )

        except Exception as error:
            print(
                f"Ошибка источника "
                f"{source_name}: "
                f"{type(error).__name__}: "
                f"{error}"
            )

    if not all_posts:
        print("Новых рецептов нет.")
        return

    # Удаляем дубли внутри текущего запуска.
    unique_posts = []
    seen_message_ids: set[int] = set()

    for post in all_posts:
        if post.message_id in seen_message_ids:
            continue

        seen_message_ids.add(
            post.message_id
        )

        unique_posts.append(post)

    print(
        "Всего получено публикаций: "
        f"{len(all_posts)}; "
        "после удаления дублей: "
        f"{len(unique_posts)}"
    )

    published_count = 0
    copied_to_news_count = 0

    for post in unique_posts:
        try:
            result = publish_recipe(post)

            print(result)

            message_id = (
                extract_published_message_id(
                    result
                )
            )

            if message_id is None:
                continue

            published_count += 1

            try:
                news_message_id = copy_message(
                    message_id
                )

                copied_to_news_count += 1

                print(
                    "Рецепт переслан "
                    "в News Radar.",
                    f"Food message_id: "
                    f"{message_id}.",
                    f"News message_id: "
                    f"{news_message_id}.",
                )

            except Exception as error:
                print(
                    "Рецепт опубликован "
                    "в Food Radar, но не удалось "
                    "переслать его в News Radar:",
                    f"{type(error).__name__}: "
                    f"{error}",
                )

        except Exception as error:
            print(
                "Ошибка обработки публикации "
                f"{post.source_url}: "
                f"{type(error).__name__}: "
                f"{error}"
            )

    print(
        "Food Radar завершён. "
        f"Опубликовано рецептов: "
        f"{published_count}. "
        f"Переслано в News Radar: "
        f"{copied_to_news_count}."
    )


if __name__ == "__main__":
    main()
