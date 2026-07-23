from __future__ import annotations

from food_service import publish_recipe
from food_to_news import copy_message
from sources.rss_food_source import RssFoodSource
from sources.telegram_source import TelegramSource
from sources.youtube_source import YouTubeSource


def main() -> None:
    """
    Запускает все подключённые источники Food Radar.

    Ошибка одного источника не останавливает остальные.
    """
    sources = [
        RssFoodSource(),
        TelegramSource(),
        YouTubeSource(),
    ]

    all_posts = []

    for source in sources:
        source_name = source.__class__.__name__

        try:
            print(f"Запуск источника: {source_name}")
            posts = source.fetch()
            all_posts.extend(posts)

            print(
                f"Источник {source_name} завершён. "
                f"Получено: {len(posts)}"
            )
        except Exception as error:
            print(
                f"Ошибка источника {source_name}: "
                f"{error}"
            )

    if not all_posts:
        print("Новых рецептов нет.")
        return

    # Удаляем дубли внутри одного запуска.
    unique_posts = []
    seen_message_ids: set[int] = set()

    for post in all_posts:
        if post.message_id in seen_message_ids:
            continue

        seen_message_ids.add(post.message_id)
        unique_posts.append(post)

    print(
        "Всего получено публикаций: "
        f"{len(all_posts)}; "
        f"после удаления дублей: {len(unique_posts)}"
    )

    for post in unique_posts:
        try:
            result = publish_recipe(post)

            result_text = str(result)

            if result_text.startswith(
                "Рецепт опубликован"
            ):
                message_id = int(
                    result_text.split(":")[-1].strip()
                )

                copy_message(message_id)

            print(result)

        except Exception as error:
            print(
                "Ошибка обработки публикации "
                f"{post.source_url}: {error}"
            )


if __name__ == "__main__":
    main()
