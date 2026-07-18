import os
import json
import hashlib
import html
from pathlib import Path
from urllib.parse import urlparse

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
    ("Коммерсант", "https://www.kommersant.ru/RSS/news.xml"),
    ("РБК", "https://rssexport.rbc.ru/rbcnews/news/30/full.rss"
    ("Интерфакс", "https://www.interfax.ru/rss.asp"),
    ("Reuters World", "https://feeds.reuters.com/Reuters/worldNews"),
    ("Associated Press", "https://apnews.com/rss"),
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("International Crisis Group", "https://www.crisisgroup.org/rss-0"),
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

def source_domain(link):
    return urlparse(link).netloc.replace("www.", "")

def collect():
    items = []

    for source, url in FEEDS:
        try:
            response = requests.get(
                url,
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0 NewsRadarBot/1.0"},
            )
            response.raise_for_status()

            feed = feedparser.parse(response.content)

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

                items.append({
                    "source": source,
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "score": score(title, summary, source),
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

def send(text):
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHANNEL,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(data)

def main():
    posted = load_posted()
    count = 0
    for item in collect():
        key = fingerprint(item["title"], item["link"])
        if key in posted:
            continue
        send(build_post(item))
        posted.add(key)
        count += 1
        print(f"Опубликовано: {item['title']}")
        if count >= POSTS_PER_RUN:
            break
    save_posted(posted)
    print(f"Готово. Новых публикаций: {count}")

if __name__ == "__main__":
    main()
