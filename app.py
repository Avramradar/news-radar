import os
import json
import hashlib
import html
from pathlib import Path
from urllib.parse import urlparse
from urllib.parse import urljoin, urljoin
from bs4 import BeautifulSoup

import feedparser
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL = os.getenv("CHANNEL", "@newsRadar2026")
POSTS_PER_RUN = int(os.getenv("POSTS_PER_RUN", "2"))
STATE_FILE = Path("posted.json")

FEEDS = [
    # Общие новости России и мира
    ("ТАСС", "https://tass.ru/rss/v2.xml"),
    ("Коммерсантъ", "https://www.kommersant.ru/RSS/news.xml"),
    ("РБК", "https://rssexport.rbc.ru/rbcnews/news/30/full.rss"),
    ("Reuters World", "https://feeds.reuters.com/Reuters/worldNews"),
    ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
    ("The Guardian World", "https://www.theguardian.com/world/rss"),
    ("Associated Press", "https://apnews.com/hub/ap-top-news?output=rss"),
    ("Euronews", "https://www.euronews.com/rss"),

    # Международные организации
    ("ООН Новости", "https://news.un.org/feed/subscribe/ru/news/all/rss.xml"),
    ("МККК", "https://www.icrc.org/en/rss"),

    # Экономика и официальные данные
    ("Банк России", "https://www.cbr.ru/rss/RssNews"),

    # Наука
    ("N+1", "https://nplus1.ru/rss"),
    ("NASA", "https://www.nasa.gov/rss/dyn/breaking_news.rss"),
    ("ESA", "https://www.esa.int/rssfeed/Our_Activities"),
    ("ScienceDaily", "https://www.sciencedaily.com/rss/all.xml"),

    # Технологии
    ("Хабр", "https://habr.com/ru/rss/articles/?fl=ru"),
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ("Migration Policy Institute", "https://www.migrationpolicy.org/rss.xml"),
    ("Migration Policy Institute Europe", "https://www.migrationpolicy.org/rss/taxonomy-term/66"),
    ("Коммерсант", "https://www.kommersant.ru/RSS/news.xml"),
    ("РБК", "https://rssexport.rbc.ru/rbcnews/news/30/full.rss"),
    ("Интерфакс", "https://www.interfax.ru/rss.asp"),
    ("Reuters World", "https://feeds.reuters.com/Reuters/worldNews"),
    ("Associated Press", "https://apnews.com/rss"),
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("International Crisis Group", "https://www.crisisgroup.org/rss-0"),
] 

SOURCE_WEIGHTS = {
    # Официальные данные и первичные источники
    "Банк России": 4,
    "ООН Новости": 3,
    "NASA": 3,
    "ESA": 3,
    "Migration Policy Institute": 4,
    "Migration Policy Institute Europe": 4,
    "Reuters World": 5,
    "Associated Press": 5,
    "International Crisis Group": 5,
    "Интерфакс": 4,
    "Коммерсант": 4,
    "BBC World": 4,

    # Наука и технологии
    "N+1": 3,
    "ScienceDaily": 2,
    "Ars Technica": 2,
    "Хабр": 2,
    "TechCrunch": 2,
    "The Verge": 1,

    # Общая новостная повестка
    "РБК": 2,
    "ТАСС": 1,
} 
KEYWORDS = {
    "срочно": 5, "война": 4, "переговор": 4, "санкц": 4,
    "эконом": 3, "нефть": 3, "газ": 3, "рынок": 3,
    "инфляц": 3, "банк": 3, "искусственн": 3, "ии": 3,
    "технолог": 2, "космос": 2, "наука": 2, "выбор": 3,
    "правитель": 3, "президент": 3, "катастроф": 5,
    "авар": 4, "землетряс": 5, "пожар": 4, "атака": 5,
    "иммигра": 4,
    "эмигра": 4,
    "виза": 4,
    "вид на жительство": 5,
    "внж": 5,
    "пмж": 5,
    "гражданство": 5,
    "рабочая виза": 5,
    "цифровой кочевник": 4,
    "рынок труда": 3,
    "стоимость жизни": 3,
    "признание диплома": 4,
    "семейное воссоединение": 4,
    "убежище": 3,
    "temporary protection": 4,
    "residence permit": 5,
    "work permit": 5,
    "immigration": 4,
    "visa": 4,
    "citizenship": 5,
    "переговоры": 5,
    "санкции": 5,
    "МИД": 4,
    "Кремль": 4,
    "Госдума": 3,
    "Минобороны": 4,
    "армия": 4,
    "беспилотник": 5,
    "БПЛА": 5,
    "удар": 4,
    "фронт": 4,
    "наступление": 5,
    "оборона": 4,
    "дипломатия": 4,
    "NATO": 4,
    "Ukraine": 4,
    "Russia": 4,
    "ceasefire": 5,
}

def clean(value):
    value = html.unescape(value or "").replace("\n", " ").replace("\r", " ")
    return " ".join(value.split()).strip()

def fingerprint(title, link):
    raw = f"{title.lower().strip()}|{link.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def load_posted():
    if not STATE_FILE.exists():
        return set()
    try:
        return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    except Exception:
        return set()

def save_posted(posted):
    STATE_FILE.write_text(
        json.dumps(sorted(posted)[-3000:], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

def score(title, summary, source):
    text = f"{title} {summary}".lower()

    value = SOURCE_WEIGHTS.get(source, 0)

    value += sum(
        weight
        for word, weight in KEYWORDS.items()
        if word in text
    )

    # Повышаем вес конкретных данных
    fact_markers = [
        "%", "млрд", "млн", "рубл", "доллар",
        "заявил", "сообщил", "опубликовал",
        "исследование", "ученые", "данные",
    ]

    value += sum(1 for marker in fact_markers if marker in text)

    # Снижаем вес эмоциональных и кликбейтных формулировок
    clickbait_markers = [
        "шок", "сенсац", "ужас", "немыслим",
        "все пропало", "срочно смотрите",
        "вы не поверите", "разгром", "истерик",
        "унизил", "взорвал интернет",
    ]

    value -= sum(3 for marker in clickbait_markers if marker in text)

    return value
def valid_image_url(image_url):
    if not image_url:
        return False

    try:
        response = requests.get(
            image_url,
            timeout=10,
            stream=True,
            allow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Linux; Android 10) "
                    "AppleWebKit/537.36 Chrome/120 Safari/537.36"
                )
            },
        )

        content_type = response.headers.get("Content-Type", "").lower()
        return response.ok and content_type.startswith("image/")

    except Exception:
        return False


def find_image(entry, article_url):
    candidates = []

    # Изображения, указанные непосредственно в RSS
    for media in entry.get("media_content", []):
        url = media.get("url")
        media_type = media.get("type", "")

        if url and (not media_type or media_type.startswith("image/")):
            candidates.append(url)

    for thumbnail in entry.get("media_thumbnail", []):
        url = thumbnail.get("url")
        if url:
            candidates.append(url)

    for enclosure in entry.get("enclosures", []):
        url = enclosure.get("href") or enclosure.get("url")
        enclosure_type = enclosure.get("type", "")

        if url and enclosure_type.startswith("image/"):
            candidates.append(url)

    # Проверяем, что RSS действительно дал изображение
    for image_url in candidates:
        image_url = urljoin(article_url, image_url)

        if valid_image_url(image_url):
            return image_url

    # Пытаемся найти og:image на странице статьи
    try:
        response = requests.get(
            article_url,
            timeout=10,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Linux; Android 10) "
                    "AppleWebKit/537.36 Chrome/120 Safari/537.36"
                )
            },
        )

        if not response.ok:
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        tags = [
            soup.find("meta", property="og:image"),
            soup.find("meta", property="og:image:url"),
            soup.find("meta", attrs={"name": "twitter:image"}),
            soup.find("meta", attrs={"name": "twitter:image:src"}),
        ]

        for tag in tags:
            if not tag:
                continue

            image_url = tag.get("content")
            image_url = urljoin(article_url, image_url)

            if valid_image_url(image_url):
                return image_url

    except Exception as error:
        print(f"Не удалось получить картинку для {article_url}: {error}")

    return None
STOP_WORDS = {
    "что", "как", "для", "это", "его", "она", "они", "при",
    "или", "уже", "после", "будет", "были", "стал", "стала",
    "из-за", "свой", "свои", "также", "сообщил", "заявил",
    "the", "and", "for", "with", "from", "that", "this",
    "after", "over", "into", "says", "said",
}


def title_words(title):
    text = clean(title).lower()

    for symbol in ".,:;!?()[]{}«»\"'—–-/":
        text = text.replace(symbol, " ")

    return {
        word
        for word in text.split()
        if len(word) >= 4 and word not in STOP_WORDS
    }


def similar_titles(first_title, second_title):
    first = title_words(first_title)
    second = title_words(second_title)

    if not first or not second:
        return False

    common = len(first & second)
    smallest = min(len(first), len(second))

    return common / smallest >= 0.65


def remove_duplicates(items):
    unique_items = []

    # Сначала идут новости с самым высоким рейтингом
    for item in items:
        duplicate = any(
            similar_titles(item["title"], saved["title"])
            for saved in unique_items
        )

        if duplicate:
            print(f"Пропущен дубль: {item['title']}")
            continue

        unique_items.append(item)

    return unique_items
def collect():
    items = []

    for source, url in FEEDS:
        try:
            feed = feedparser.parse(url)

            if feed.bozo and not feed.entries:
                print(f"Ошибка RSS: {source}")
                continue

            added = 0

            for entry in feed.entries[:20]:
                title = clean(getattr(entry, "title", ""))
                link = clean(getattr(entry, "link", ""))
                summary = clean(getattr(entry, "summary", ""))

                if len(title) < 20 or not link:
                    continue

                news_score = score(title, summary, source)

                items.append({
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "source": source,
                    "score": news_score,
                    "image": find_image(entry, link),
                })

                added += 1

            print(f"{source}: получено {added} новостей")

        except Exception as error:
            print(f"Источник временно недоступен: {source} — {error}")
            continue

        sorted_items = sorted(
        items,
        key=lambda item: item["score"],
        reverse=True,
    )

    return remove_duplicates(sorted_items)
    )
def source_domain(url):
    try:
        domain = urlparse(url).netloc.lower()
        return domain.removeprefix("www.")
    except Exception:
        return ""
def build_post(item):
    title = html.escape(item["title"])

    summary = clean(item["summary"])

    # Удаляем HTML
    summary = BeautifulSoup(summary, "html.parser").get_text(" ", strip=True)

    # Удаляем дубли заголовка
    if summary.lower().startswith(item["title"].lower()):
        summary = summary[len(item["title"]):].strip()

    if len(summary) > 280:
        summary = summary[:277].rsplit(" ", 1)[0] + "..."

    label = "🚨 СРОЧНО" if item["score"] >= 12 else "⚡ ВАЖНО" if item["score"] >= 8 else "📰 NEWS RADAR"

    text = f"""
<b>{label}</b>

<b>{title}</b>

{html.escape(summary)}

🌍 <b>Источник:</b> {html.escape(item["source"])}

🔗 <a href="{html.escape(item["link"], quote=True)}">Читать полностью</a>

────────────
📡 <b>NEWS RADAR</b>

🔔 Подпишись:
👉 @newsRadar2026
"""

    return text.strip()

def send(text, image_url=None):
    # Сначала пробуем отправить публикацию с фотографией
    if image_url:
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                data={
                    "chat_id": CHANNEL,
                    "photo": image_url,
                    "caption": text[:1024],
                    "parse_mode": "HTML",
                },
                timeout=20,
            )

            if response.ok:
                return True

            print("Telegram не принял фото:", response.text)

        except Exception as error:
            print(f"Ошибка отправки фото: {error}")

    # Если фото не подошло — отправляем обычный текстовый пост
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={
                "chat_id": CHANNEL,
                "text": text[:4096],
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=20,
        )

        if not response.ok:
            print("Telegram не принял текст:", response.text)
            return False

        return True

    except Exception as error:
        print(f"Ошибка отправки текста: {error}")
        return False

def main():
    posted = load_posted()
    count = 0

    for item in collect():
        key = fingerprint(item["title"], item["link"])

        if key in posted:
            continue

        success = send(
            build_post(item),
            item.get("image"),
        )

        if not success:
            print(f"Не удалось опубликовать: {item['title']}")
            continue

        posted.add(key)
        count += 1
        print(f"Опубликовано: {item['title']}")

        if count >= POSTS_PER_RUN:
            break

    save_posted(posted)
    print(f"Готово. Новых публикаций: {count}")


if __name__ == "__main__":
    main()
        
 
