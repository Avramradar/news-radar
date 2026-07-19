import os
import json
import hashlib
import html
from pathlib import Path
from urllib.parse import urlparse, urljoin
from deep_translator import GoogleTranslator
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta

import feedparser
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL = os.getenv("CHANNEL", "@newsRadar2026")
POSTS_PER_RUN = int(os.getenv("POSTS_PER_RUN", "2"))
STATE_FILE = Path("posted.json")

FEEDS = [
    # 🇷🇺 Россия
    {
        "name": "ТАСС",
        "url": "https://tass.ru/rss/v2.xml",
        "category": "РОССИЯ",
        "icon": "🇷🇺",
        "language": "ru",
        "weight": 8,
    },
    {
        "name": "Интерфакс",
        "url": "https://www.interfax.ru/rss.asp",
        "category": "РОССИЯ",
        "icon": "🇷🇺",
        "language": "ru",
        "weight": 8,
    },
    {
        "name": "Коммерсантъ",
        "url": "https://www.kommersant.ru/RSS/news.xml",
        "category": "РОССИЯ",
        "icon": "🇷🇺",
        "language": "ru",
        "weight": 7,
    },
    {
        "name": "РБК",
        "url": "https://rssexport.rbc.ru/rbcnews/news/30/full.rss",
        "category": "РОССИЯ",
        "icon": "🇷🇺",
        "language": "ru",
        "weight": 7,
    },

    # 🌍 Мир
    {
        "name": "BBC World",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "category": "МИРОВЫЕ НОВОСТИ",
        "icon": "🌍",
        "language": "en",
        "weight": 9,
    },
    {
        "name": "The Guardian",
        "url": "https://www.theguardian.com/world/rss",
        "category": "МИРОВЫЕ НОВОСТИ",
        "icon": "🌍",
        "language": "en",
        "weight": 8,
    },
    {
        "name": "Al Jazeera",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "category": "МИРОВЫЕ НОВОСТИ",
        "icon": "🌍",
        "language": "en",
        "weight": 8,
    },
    {
        "name": "NPR World",
        "url": "https://feeds.npr.org/1004/rss.xml",
        "category": "МИРОВЫЕ НОВОСТИ",
        "icon": "🌍",
        "language": "en",
        "weight": 8,
    },
    {
        "name": "Le Monde International",
        "url": "https://www.lemonde.fr/en/international/rss_full.xml",
        "category": "МИРОВЫЕ НОВОСТИ",
        "icon": "🌍",
        "language": "en",
        "weight": 8,
    },
    {
        "name": "Le Monde Europe",
        "url": "https://www.lemonde.fr/en/europe/rss_full.xml",
        "category": "ЕВРОПА",
        "icon": "🇪🇺",
        "language": "en",
        "weight": 7,
    },
    {
        "name": "International Crisis Group",
        "url": "https://www.crisisgroup.org/rss-0",
        "category": "МИРОВЫЕ НОВОСТИ",
        "icon": "🌍",
        "language": "en",
        "weight": 9,
    },

    # 💰 Экономика
    {
        "name": "Банк России",
        "url": "https://www.cbr.ru/rss/RssNews",
        "category": "ЭКОНОМИКА",
        "icon": "💰",
        "language": "ru",
        "weight": 9,
    },
    {
        "name": "Банк России — пресс-релизы",
        "url": "https://www.cbr.ru/rss/RssPress",
        "category": "ЭКОНОМИКА",
        "icon": "💰",
        "language": "ru",
        "weight": 9,
    },
    {
        "name": "Le Monde Economy",
        "url": "https://www.lemonde.fr/en/world-economy/rss_full.xml",
        "category": "ЭКОНОМИКА",
        "icon": "💰",
        "language": "en",
        "weight": 7,
    },

    # 🤖 Технологии и ИИ
    {
        "name": "Хабр",
        "url": "https://habr.com/ru/rss/articles/?fl=ru",
        "category": "ТЕХНОЛОГИИ И ИИ",
        "icon": "🤖",
        "language": "ru",
        "weight": 6,
    },
    {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/",
        "category": "ТЕХНОЛОГИИ И ИИ",
        "icon": "🤖",
        "language": "en",
        "weight": 7,
    },
    {
        "name": "The Verge",
        "url": "https://www.theverge.com/rss/index.xml",
        "category": "ТЕХНОЛОГИИ И ИИ",
        "icon": "🤖",
        "language": "en",
        "weight": 7,
    },
    {
        "name": "Ars Technica",
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "category": "ТЕХНОЛОГИИ И ИИ",
        "icon": "🤖",
        "language": "en",
        "weight": 8,
    },
    {
        "name": "MIT Technology Review",
        "url": "https://www.technologyreview.com/feed/",
        "category": "ТЕХНОЛОГИИ И ИИ",
        "icon": "🤖",
        "language": "en",
        "weight": 8,
    },
    {
        "name": "Le Monde AI",
        "url": "https://www.lemonde.fr/en/artificial-intelligence/rss_full.xml",
        "category": "ТЕХНОЛОГИИ И ИИ",
        "icon": "🤖",
        "language": "en",
        "weight": 7,
    },

    # 🔬 Наука
    {
        "name": "N+1",
        "url": "https://nplus1.ru/rss",
        "category": "НАУКА",
        "icon": "🔬",
        "language": "ru",
        "weight": 7,
    },
    {
        "name": "ScienceDaily",
        "url": "https://www.sciencedaily.com/rss/all.xml",
        "category": "НАУКА",
        "icon": "🔬",
        "language": "en",
        "weight": 7,
    },
    {
        "name": "Nature",
        "url": "https://www.nature.com/nature.rss",
        "category": "НАУКА",
        "icon": "🔬",
        "language": "en",
        "weight": 9,
    },
    {
        "name": "Phys.org",
        "url": "https://phys.org/rss-feed/",
        "category": "НАУКА",
        "icon": "🔬",
        "language": "en",
        "weight": 7,
    },
    {
        "name": "Le Monde Science",
        "url": "https://www.lemonde.fr/en/science/rss_full.xml",
        "category": "НАУКА",
        "icon": "🔬",
        "language": "en",
        "weight": 7,
    },

    # 🚀 Космос
    {
        "name": "NASA",
        "url": "https://www.nasa.gov/feed/",
        "category": "КОСМОС",
        "icon": "🚀",
        "language": "en",
        "weight": 9,
    },
    {
        "name": "ESA",
        "url": "https://www.esa.int/rssfeed/Our_Activities",
        "category": "КОСМОС",
        "icon": "🚀",
        "language": "en",
        "weight": 8,
    },
    {
        "name": "Le Monde Space",
        "url": "https://www.lemonde.fr/en/space-and-astronomy/rss_full.xml",
        "category": "КОСМОС",
        "icon": "🚀",
        "language": "en",
        "weight": 7,
    },

    # 🏥 Международные организации
    {
        "name": "ООН Новости",
        "url": "https://news.un.org/feed/subscribe/ru/news/all/rss.xml",
        "category": "МЕЖДУНАРОДНЫЕ ОРГАНИЗАЦИИ",
        "icon": "🏥",
        "language": "ru",
        "weight": 9,
    },
    {
        "name": "МККК",
        "url": "https://www.icrc.org/en/rss",
        "category": "МЕЖДУНАРОДНЫЕ ОРГАНИЗАЦИИ",
        "icon": "🏥",
        "language": "en",
        "weight": 8,
    },

    # 🧠 Интересные факты
    {
        "name": "Today I Found Out",
        "url": "https://www.todayifoundout.com/index.php/feed/",
        "category": "ИНТЕРЕСНЫЙ ФАКТ",
        "icon": "🧠",
        "language": "en",
        "weight": 4,
    },
    {
        "name": "Damn Interesting",
        "url": "https://www.damninteresting.com/feed/",
        "category": "ИНТЕРЕСНЫЙ ФАКТ",
        "icon": "🧠",
        "language": "en",
        "weight": 4,
    },
    {
        "name": "Now I Know",
        "url": "https://nowiknow.com/feed/",
        "category": "ИНТЕРЕСНЫЙ ФАКТ",
        "icon": "🧠",
        "language": "en",
        "weight": 4,
    },
]


SOURCE_WEIGHTS = {
    feed["name"]: feed["weight"]
    for feed in FEEDS
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
TRANSLATION_CACHE = {}


def has_cyrillic(text):
    """Проверяет, присутствует ли в тексте кириллица."""
    return any("а" <= char.lower() <= "я" or char.lower() == "ё"
               for char in text)


def translate_to_russian(text, language="auto"):
    """
    Переводит текст на русский.

    При любой ошибке возвращает исходный текст,
    поэтому публикация не будет сорвана.
    """
    text = clean(text)

    if not text:
        return ""

    if language == "ru" or has_cyrillic(text):
        return text

    cache_key = text[:4500]

    if cache_key in TRANSLATION_CACHE:
        return TRANSLATION_CACHE[cache_key]

    try:
        translated = GoogleTranslator(
            source="auto",
            target="ru",
        ).translate(cache_key)

        translated = clean(translated)

        if translated:
            TRANSLATION_CACHE[cache_key] = translated
            return translated

    except Exception as error:
        print(f"Перевод временно недоступен: {error}")

    return text
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
    """Ищет подходящее изображение новости в RSS и на странице статьи."""

    candidates = []

    def add_candidate(url):
        if not url:
            return

        url = str(url).strip()
        if not url:
            return

        absolute_url = urljoin(article_url, url)

        lower_url = absolute_url.lower()

        # Не используем логотипы, иконки, аватары и рекламные картинки
        blocked_words = (
            "logo",
            "icon",
            "avatar",
            "favicon",
            "sprite",
            "banner",
            "advert",
            "pixel",
            "tracker",
            "placeholder",
            "default-image",
        )

        if any(word in lower_url for word in blocked_words):
            return

        if absolute_url not in candidates:
            candidates.append(absolute_url)

    # 1. Картинки непосредственно из RSS
    for media in entry.get("media_content", []):
        media_type = media.get("type", "")
        url = media.get("url")

        if url and (not media_type or media_type.startswith("image/")):
            add_candidate(url)

    for thumbnail in entry.get("media_thumbnail", []):
        add_candidate(thumbnail.get("url"))

    for enclosure in entry.get("enclosures", []):
        enclosure_type = enclosure.get("type", "")
        url = enclosure.get("href") or enclosure.get("url")

        if url and (
            enclosure_type.startswith("image/")
            or not enclosure_type
        ):
            add_candidate(url)

    # 2. Картинки внутри описания RSS
    rss_html_parts = [
        entry.get("summary", ""),
        entry.get("description", ""),
    ]

    content_parts = entry.get("content", [])
    if isinstance(content_parts, list):
        for content_part in content_parts:
            if isinstance(content_part, dict):
                rss_html_parts.append(content_part.get("value", ""))

    for rss_html in rss_html_parts:
        if not rss_html:
            continue

        try:
            rss_soup = BeautifulSoup(rss_html, "html.parser")

            for image_tag in rss_soup.find_all("img"):
                add_candidate(
                    image_tag.get("src")
                    or image_tag.get("data-src")
                    or image_tag.get("data-original")
                    or image_tag.get("data-lazy-src")
                )

        except Exception as error:
            print("Ошибка разбора картинки из RSS:", error)

    # Сначала проверяем кандидатов из RSS
    for image_url in candidates:
        if valid_image_url(image_url):
            return image_url

    # 3. Загружаем страницу оригинальной статьи
    try:
        response = requests.get(
            article_url,
            timeout=15,
            allow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Linux; Android 10) "
                    "AppleWebKit/537.36 "
                    "Chrome/120.0 Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,*/*;q=0.8"
                ),
                "Accept-Language": "ru,en;q=0.8",
            },
        )

        if not response.ok:
            print(
                f"Страница статьи недоступна: "
                f"{response.status_code} {article_url}"
            )
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # 4. Главные изображения из метатегов
        meta_selectors = [
            ("property", "og:image"),
            ("property", "og:image:url"),
            ("property", "og:image:secure_url"),
            ("name", "twitter:image"),
            ("name", "twitter:image:src"),
            ("itemprop", "image"),
        ]

        for attribute, value in meta_selectors:
            tag = soup.find("meta", attrs={attribute: value})

            if tag:
                add_candidate(tag.get("content"))

        # 5. Изображения из JSON-LD
        import json

        for script in soup.find_all(
            "script",
            attrs={"type": "application/ld+json"},
        ):
            try:
                raw_json = script.string or script.get_text()
                data = json.loads(raw_json)

                json_objects = data if isinstance(data, list) else [data]

                for json_object in json_objects:
                    if not isinstance(json_object, dict):
                        continue

                    graph = json_object.get("@graph", [])
                    objects = (
                        graph
                        if isinstance(graph, list)
                        else [json_object]
                    )

                    if not graph:
                        objects = [json_object]

                    for obj in objects:
                        if not isinstance(obj, dict):
                            continue

                        image = obj.get("image")
                        thumbnail = obj.get("thumbnailUrl")

                        if isinstance(image, str):
                            add_candidate(image)

                        elif isinstance(image, list):
                            for image_item in image:
                                if isinstance(image_item, str):
                                    add_candidate(image_item)
                                elif isinstance(image_item, dict):
                                    add_candidate(
                                        image_item.get("url")
                                        or image_item.get("contentUrl")
                                    )

                        elif isinstance(image, dict):
                            add_candidate(
                                image.get("url")
                                or image.get("contentUrl")
                            )

                        add_candidate(thumbnail)

            except Exception:
                continue

        # 6. Обычные фотографии внутри статьи
        article_container = (
            soup.find("article")
            or soup.find("main")
            or soup
        )

        for image_tag in article_container.find_all("img", limit=30):
            width = image_tag.get("width")
            height = image_tag.get("height")

            try:
                if width and int(str(width).replace("px", "")) < 300:
                    continue
                if height and int(str(height).replace("px", "")) < 180:
                    continue
            except ValueError:
                pass

            add_candidate(
                image_tag.get("data-src")
                or image_tag.get("data-original")
                or image_tag.get("data-lazy-src")
                or image_tag.get("src")
            )

            srcset = (
                image_tag.get("srcset")
                or image_tag.get("data-srcset")
            )

            if srcset:
                srcset_items = []

                for part in srcset.split(","):
                    pieces = part.strip().split()

                    if not pieces:
                        continue

                    image_src = pieces[0]
                    size = 0

                    if len(pieces) > 1 and pieces[1].endswith("w"):
                        try:
                            size = int(pieces[1][:-1])
                        except ValueError:
                            size = 0

                    srcset_items.append((size, image_src))

                if srcset_items:
                    srcset_items.sort(reverse=True)
                    add_candidate(srcset_items[0][1])

        # Проверяем все найденные картинки
        for image_url in candidates:
            if valid_image_url(image_url):
                return image_url

    except Exception as error:
        print(
            f"Не удалось получить картинку для "
            f"{article_url}: {error}"
        )

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

    for feed_info in FEEDS:
        source = feed_info["name"]
        url = feed_info["url"]
        category = feed_info["category"]
        icon = feed_info["icon"]
        language = feed_info["language"]

        try:
            feed = feedparser.parse(url)

            if feed.bozo and not feed.entries:
                print(f"Ошибка RSS: {source}")
                continue

            added = 0

            for entry in feed.entries[:20]:
                title = clean(getattr(entry, "title", ""))
                link = clean(getattr(entry, "link", ""))
                summary = clean(
                    getattr(entry, "summary", "")
                    or getattr(entry, "description", "")
                )

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
                    "category": category,
                    "icon": icon,
                    "language": language,
                })

                added += 1

            print(f"{icon} {source}: получено {added} новостей")

        except Exception as error:
            print(
                f"Источник временно недоступен: "
                f"{source} — {error}"
            )
            continue

    sorted_items = sorted(
        items,
        key=lambda item: item["score"],
        reverse=True,
    )

    return remove_duplicates(sorted_items)

def source_domain(url):
    try:
        domain = urlparse(url).netloc.lower()
        return domain.removeprefix("www.")
    except Exception:
        return ""
def build_post(item):
    original_title = clean(item.get("title", ""))
    original_summary = clean(item.get("summary", ""))

    language = item.get("language", "auto")
    icon = item.get("icon", "📰")
    category = item.get("category", "НОВОСТИ")

    translated_title = translate_to_russian(
        original_title,
        language,
    )

    # Сначала очищаем описание от HTML
    plain_summary = BeautifulSoup(
        original_summary,
        "html.parser",
    ).get_text(" ", strip=True)

    if plain_summary.lower().startswith(
        original_title.lower()
    ):
        plain_summary = plain_summary[
            len(original_title):
        ].strip()

    translated_summary = translate_to_russian(
        plain_summary,
        language,
    )

    if len(translated_summary) > 320:
        translated_summary = (
            translated_summary[:317].rsplit(" ", 1)[0]
            + "..."
        )

    source_name = item.get(
        "source",
        "Неизвестный источник",
    )
    article_link = item.get("link", "")

    safe_title = html.escape(translated_title)
    safe_summary = html.escape(translated_summary)
    safe_source = html.escape(source_name)
    safe_link = html.escape(article_link, quote=True)
    safe_category = html.escape(category)

    if item.get("score", 0) >= 12:
        importance = "🚨 СРОЧНО"
    elif item.get("score", 0) >= 8:
        importance = "⚡ ВАЖНО"
    else:
        importance = ""

    heading = f"{icon} {safe_category}"

    if importance:
        heading += f" · {importance}"

    text = f"""
<b>{heading}</b>

<b>{safe_title}</b>

📝 {safe_summary}

{icon} <b>Источник:</b> {safe_source}

🔗 <b>Оригинал:</b>
{safe_link}

━━━━━━━━━━━━━━
📡 <b>NEWS RADAR</b>
🔔 @newsRadar2026
"""

    return text.strip()
def fit_caption(text, limit=1024):
    """Сокращает подпись к фотографии, сохраняя источник и ссылку."""
    if len(text) <= limit:
        return text

    marker = "\n🌍 <b>Источник:</b>"
    marker_position = text.find(marker)

    if marker_position == -1:
        return text[:limit - 1].rstrip() + "…"

    ending = text[marker_position:]
    available = limit - len(ending) - 3

    if available < 100:
        return text[:limit - 1].rstrip() + "…"

    beginning = text[:available].rstrip()

    return beginning + "…\n" + ending
    DIGEST_KEYWORDS = {
    "война": 5,
    "атака": 4,
    "удар": 4,
    "кризис": 4,
    "санкции": 4,
    "переговоры": 4,
    "президент": 3,
    "правительство": 3,
    "экономика": 3,
    "нефть": 3,
    "газ": 3,
    "рынок": 3,
    "банк": 3,
    "инфляция": 3,
    "искусственный интеллект": 4,
    "ии": 3,
    "технологии": 2,
    "наука": 2,
    "космос": 3,
    "nasa": 3,
    "war": 5,
    "attack": 4,
    "crisis": 4,
    "sanctions": 4,
    "economy": 3,
    "market": 3,
    "artificial intelligence": 4,
    "technology": 2,
    "science": 2,
    "space": 3,
}


def digest_entry_time(entry):
    """Возвращает время публикации RSS-записи в UTC."""
    for field in ("published_parsed", "updated_parsed"):
        value = entry.get(field)

        if value:
            try:
                return datetime(
                    value.tm_year,
                    value.tm_mon,
                    value.tm_mday,
                    value.tm_hour,
                    value.tm_min,
                    value.tm_sec,
                    tzinfo=timezone.utc,
                )
            except Exception:
                continue

    return None


def digest_score(title, summary):
    """Оценивает важность новости для сводки."""
    combined = f"{title} {summary}".lower()
    score = 0

    for keyword, weight in DIGEST_KEYWORDS.items():
        if keyword in combined:
            score += weight

    return score


def collect_digest_items(hours=12):
    """Собирает новости из всех RSS без изменения posted.json."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    items = []

    for feed_info in FEEDS:
        source_name = feed_info["name"]
        feed_url = feed_info["url"]
        language = feed_info["language"]
        category = feed_info["category"]
        icon = feed_info["icon"]
        try:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:20]:
                title = clean(entry.get("title", ""))
                link = entry.get("link", "")
                summary = clean(
                    entry.get("summary")
                    or entry.get("description")
                    or ""
                )

                if not title or not link:
                    continue

                published_at = digest_entry_time(entry)

                # Записи без даты принимаем, записи старше 12 часов пропускаем
                if published_at and published_at < cutoff:
                    continue

                items.append({
                    "language": language,
                    "category": category,
                    "icon": icon,
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "source": source_name,
                    "score": digest_score(title, summary),
                    "published_at": published_at,
                })

        except Exception as error:
            print(f"Ошибка источника сводки {source_name}: {error}")

    items.sort(
        key=lambda item: (
            item["score"],
            item["published_at"] or datetime.min.replace(
                tzinfo=timezone.utc
            ),
        ),
        reverse=True,
    )

    return remove_duplicates(items)


def build_digest(items, max_items=12):
    """Создаёт расширенную утреннюю или вечернюю сводку."""
    current_hour = datetime.now().hour

    if current_hour < 15:
        digest_title = "☀️ УТРЕННЯЯ СВОДКА"
    else:
        digest_title = "🌙 ВЕЧЕРНЯЯ СВОДКА"

    selected = items[:max_items]

    if not selected:
        return (
            f"<b>{digest_title}</b>\n\n"
            "За последние часы значимых обновлений не найдено.\n\n"
            "📡 <b>NEWS RADAR</b>\n"
            "🔔 @newsRadar2026"
        )

    parts = [
        f"<b>{digest_title}</b>",
        "",
        "Главные события за последние 12 часов:",
        "",
    ]

    for number, item in enumerate(selected, start=1):
        translated_title = translate_to_russian(
        item["title"],
        item.get("language", "auto"),
        )
        safe_title = html.escape(translated_title)
        safe_source = html.escape(item["source"])
        safe_link = html.escape(item["link"], quote=True)

        parts.append(
            f"<b>{number}. {safe_title}</b>\n"
            f'{item.get("icon", "🌍")} {safe_source}\n'
            f'🔗 <a href="{safe_link}">Открыть новость</a>'
        )
        parts.append("")

        parts.extend([
        "━━━━━━━━━━━━━━",
        "📡 <b>NEWS RADAR</b>",
        "🔔 @newsRadar2026",
    ])

    text = "\n".join(parts)

    # Telegram допускает до 4096 символов в обычном сообщении
    return text[:4000]


def send_digest():
    """Собирает и отправляет сводку отдельным сообщением."""
    items = collect_digest_items(hours=12)
    text = build_digest(items)

    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={
            "chat_id": CHANNEL,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"Ошибка отправки сводки: {response.status_code} "
            f"{response.text[:500]}"
        )

    print(f"Сводка опубликована. Новостей: {min(len(items), 12)}")
def send(text, image_url=None):
    # Сначала пробуем отправить публикацию с фотографией
    if image_url:
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                data={
                    "chat_id": CHANNEL,
                    "photo": image_url,
                    "caption": fit_caption(text), 
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
    mode = os.getenv("MODE", "news").lower()

    if mode == "digest":
        send_digest()
    else:
        main()
        
 
