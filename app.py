import os
import json
import hashlib
import html
from pathlib import Path
from urllib.parse import urlparse
from urllib.parse import urljoin
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
def find_image(entry, article_url):
    # 1. Картинка из RSS media:content
    media_content = entry.get("media_content", [])
    if media_content:
        image_url = media_content[0].get("url")
        if image_url:
            return image_url

    # 2. Картинка из RSS media:thumbnail
    media_thumbnail = entry.get("media_thumbnail", [])
    if media_thumbnail:
        image_url = media_thumbnail[0].get("url")
        if image_url:
            return image_url

    # 3. Картинка из enclosure
    for enclosure in entry.get("enclosures", []):
        enclosure_type = enclosure.get("type", "")
        enclosure_url = enclosure.get("href") or enclosure.get("url")

        if enclosure_url and enclosure_type.startswith("image/"):
            return enclosure_url

    # 4. Ищем og:image на странице новости
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
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        tag = soup.find("meta", property="og:image")
        if not tag:
            tag = soup.find("meta", attrs={"name": "twitter:image"})

        if tag and tag.get("content"):
            return urljoin(article_url, tag["content"])

    except Exception as error:
        print(f"Не удалось получить картинку: {error}")

    return None
def source_domain(link):
    return urlparse(link).netloc.replace("www.", "")

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

    return sorted(
        items,
        key=lambda item: item["score"],
        reverse=True,
    )
def build_post(item):
    summary = item["summary"]
    if len(summary) > 420:
        summary = summary[:417].rsplit(" ", 1)[0] + "…"

    label = "⚡ ВАЖНО" if item["score"] >= 8 else "🛰 NEWS RADAR"
    parts = [
        f"<b>{label}</b>",
        "",
        f"<b>{html.escape(item['title'])}</b>",
    ]
    if summary:
        parts.extend(["", html.escape(summary)])
    parts.extend([
        "",
        f"Источник: {html.escape(item['source'])} · {html.escape(source_domain(item['link']))}",
        f'<a href="{html.escape(item["link"], quote=True)}">Подробнее</a>',
        "",
    ])
    parts.extend([
    "",
    "#новости #NewsRadar",
    "────────────\n📡 <b>NEWS RADAR</b>\n\n🔔 Подпишись, чтобы узнавать важные новости первым:\n👉 @newsRadar2026",
])
    return "\n".join(parts)

def send(text, image_url=None):
    if image_url:
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                data={
                    "chat_id": CHANNEL_ID,
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

    # Если картинки нет или Telegram её не принял
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={
            "chat_id": CHANNEL_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=20,
    )

    response.raise_for_status()
    return True

def main():
    posted = load_posted()
    count = 0
    for item in collect():
        key = fingerprint(item["title"], item["link"])
        if key in posted:
            continue
        send(
    build_post(item),
    item.get("image"),
)
        posted.add(key)
        count += 1
        print(f"Опубликовано: {item['title']}")
        if count >= POSTS_PER_RUN:
            break
    save_posted(posted)
    print(f"Готово. Новых публикаций: {count}")

if __name__ == "__main__":
    main()
