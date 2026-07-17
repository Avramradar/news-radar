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
    ("BBC Russian", "https://feeds.bbci.co.uk/russian/rss.xml"),
    ("DW Russian", "https://rss.dw.com/rdf/rss-ru-all"),
    ("NASA", "https://www.nasa.gov/rss/dyn/breaking_news.rss"),
    ("TechCrunch", "https://techcrunch.com/feed/"),
]

KEYWORDS = {
    "срочно": 5, "война": 4, "переговор": 4, "санкц": 4,
    "эконом": 3, "нефть": 3, "газ": 3, "рынок": 3,
    "инфляц": 3, "банк": 3, "искусственн": 3, "ии": 3,
    "технолог": 2, "космос": 2, "наука": 2, "выбор": 3,
    "правитель": 3, "президент": 3, "катастроф": 5,
    "авар": 4, "землетряс": 5, "пожар": 4, "атака": 5,
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
    STATE_FILE.write_text(json.dumps(list(posted)[-3000:], ensure_ascii=False, indent=2), encoding="utf-8")

def score(title, summary, source):
    text = f"{title} {summary}".lower()
    value = sum(weight for word, weight in KEYWORDS.items() if word in text)
    if source in {"BBC Russian", "DW Russian"}:
        value += 2
    return value

def source_domain(link):
    return urlparse(link).netloc.replace("www.", "")

def collect():
    items = []
    for source, url in FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries[:20]:
            title = clean(getattr(entry, "title", ""))
            link = clean(getattr(entry, "link", ""))
            summary = clean(getattr(entry, "summary", ""))
            if len(title) < 20 or not link:
                continue
            items.append({"source": source, "title": title, "link": link, "summary": summary, "score": score(title, summary, source)})
    return sorted(items, key=lambda item: item["score"], reverse=True)

def build_post(item):
    summary = item["summary"]
    if len(summary) > 420:
        summary = summary[:417].rsplit(" ", 1)[0] + "…"
    label = "⚡ ВАЖНО" if item["score"] >= 8 else "🛰 NEWS RADAR"
    parts = [f"<b>{label}</b>", "", f"<b>{html.escape(item['title'])}</b>"]
    if summary:
        parts.extend(["", html.escape(summary)])
    parts.extend(["", f"Источник: {html.escape(item['source'])} · {html.escape(source_domain(item['link']))}", f'<a href="{html.escape(item["link"], quote=True)}">Подробнее</a>', "", "#новости #NewsRadar"])
    return "\n".join(parts)

def send(text):
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHANNEL, "text": text, "parse_mode": "HTML", "disable_web_page_preview": False},
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(result)

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
