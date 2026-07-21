from __future__ import annotations

from food_service import publish_recipe
from sources.food_source import FoodSource
from sources.rss_food_source import RssFoodSource
from food_to_news import main as copy_food_to_news

def main() -> None:
    rss = RssFoodSource()
    posts = rss.fetch() 

    if not posts:
        print("Новых рецептов нет.")
        return

    for post in posts:
        result = publish_recipe(post)
        print(result)
        
        if str(result).startswith("Рецепт опубликован"):
            copy_food_to_news()

if __name__ == "__main__":
    main()
