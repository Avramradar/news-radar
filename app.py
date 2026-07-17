import os
import time
import sqlite3
import hashlib
import html
from datetime import datetime, timezone
from urllib.parse import urlparse

import feedparser
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL = os.getenv("CHANNEL", "@newsRadar2026")
POLL_MINUTES = int(os.getenv("POLL_MINUTES", "20"))
POSTS_PER_CYCLE = int(os.getenv("POSTS_PER_CYCLE", "2"))
MIN_TITLE_LEN = 20

FEEDS = [
    ("BBC Russian", "https://feeds.bbci.co.uk/russian/rss.xml"),
    ("DW Russian", "https://rss.dw.com/rdf/rss-ru-all"),
    ("Reuters World", "https://feeds.reuters.com/Reuters/worldNews"),
    ("NASA", "https://www.nasa.gov/rss/dyn/breaking_news.rss"),
    ("TechCrunch", "https://techcrunch.com/feed/"),
]

KEYWORDS = {
    "срочно": 5, "война": 4, "переговор": 4, "санкц": 4, "эконом": 3,
    "нефть": 3, "газ": 3, "рынок": 3, "инфляц": 3, "банк": 3,
    "искусственн": 3, "ии": 3, "технолог": 2, "космос": 2, "наука": 2,
    "выбор": 3, "правитель": 3, "президент": 3, "катастроф": 5,
    "авар": 4, "землетряс": 5, "пожар": 4, "атака": 5, "удар": 5,
}

def db():
    conn = sqlite3.connect("news.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posted (
            fingerprint TEXT PRIMARY KEY,
            title TEXT,
            link TEXT,
            posted_at TEXT
        )
    """)
    return conn

def fingerprint(title, link):
    raw = f"{title.strip().lower()}|{link.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def clean_text(value):
    value = html.unescape(value or "")
    value = value.replace("\n", " ").replace("\r", " ")
    while "  " in value:
        value = value.replace("  ", " ")
    return value.strip()

def score_item(title, summary, source):
    text = f"{title} {summary}".lower()
    score = 0
    for word, weight in KEYWORDS.items():
        if word in text:
            score += weight
    if source in {"Reuters World", "BBC Russian", "DW Russian"}:
        score += 2
    if len(title) >= 45:
        score += 1
    return score

def domain(link):
    try:
        return urlparse(link).netloc.replace("www.", "")
    except Exception:
        return ""

def build_post(item):
    title = clean_text(item["title"])
    summary = clean_text(item.get("summary", ""))
    if len(summary) > 420:
        summary = summary[:417].rsplit(" ", 1)[0] + "…"

    source = item["source"]
    link = item["link"]
    category = "⚡ ВАЖНО" if item["score"] >= 8 else "🛰 NEWS RADAR"

    body = [
        f"<b>{category}</b>",
        "",
        f"<b>{html.escape(title)}</b>",
    ]
    if summary:
        body += ["", html.escape(summary)]
    body += [
        "",
        f"Источник: {html.escape(source)} · {html.escape(domain(link))}",
        f'<a href="{html.escape(link, quote=True)}">Подробнее</a>',
        "",
        "#новости #NewsRadar"
    ]
    return "\n".join(body)

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(data)
    return data

def collect():
    items = []
    for source, feed_url in FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:20]:
            title = clean_text(getattr(entry, "title", ""))
            link = clean_text(getattr(entry, "link", ""))
            summary = clean_text(getattr(entry, "summary", ""))
            if len(title) < MIN_TITLE_LEN or not link:
                continue
            items.append({
                "source": source,
                "title": title,
                "link": link,
                "summary": summary,
                "score": score_item(title, summary, source),
            })
    items.sort(key=lambda x: x["score"], reverse=True)
    return items

def run_cycle():
    conn = db()
    posted = 0
    for item in collect():
        fp = fingerprint(item["title"], item["link"])
        exists = conn.execute(
            "SELECT 1 FROM posted WHERE fingerprint = ?", (fp,)
        ).fetchone()
        if exists:
            continue
        send_message(build_post(item))
        conn.execute(
            "INSERT INTO posted VALUES (?, ?, ?, ?)",
            (fp, item["title"], item["link"], datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
        posted += 1
        print(f"POSTED: {item['title']}", flush=True)
        if posted >= POSTS_PER_CYCLE:
            break
    if posted == 0:
        print("No new items", flush=True)

if __name__ == "__main__":
    print(f"News Radar started. Channel={CHANNEL}", flush=True)
    while True:
        try:
            run_cycle()
        except Exception as exc:
            print(f"ERROR: {type(exc).__name__}: {exc}", flush=True)
        time.sleep(POLL_MINUTES * 60)
