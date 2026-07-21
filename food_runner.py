from __future__ import annotations

from food_service import publish_recipe
from sources.food_source import FoodSource
from sources.rss_food_source import RssFoodSource
from food_to_news import copy_message 

def main() -> None:
    rss = RssFoodSource()
    posts = rss.fetch() 

    if not posts:
        print("Новых рецептов нет.")
        return

    for post in posts:
        result = publish_recipe(post)
        if str(result).startswith("Рецепт опубликован"):
            message_id = int(str(result).split(":")[-1].strip())
            copy_message(message_id)
        print(result)
     

if __name__ == "__main__":
    main()
