"""Автономный сборщик тематических Telegram-новостей."""

from __future__ import annotations

import html
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import requests

from filter import MilitaryFilter
from parser import TelegramPost, TelegramPublicParser


BASE_DIR = Path(__file__).resolve().parent
TOPIC_DIR = BASE_DIR / "military"

CHANNELS_FILE = TOPIC_DIR / "channels.txt"
CONFIG_FILE = TOPIC_DIR / "config.json"
STATE_FILE = TOPIC_DIR / "state.json"

TELEGRAM_TIMEOUT = 20
MAX_MESSAGE_LENGTH = 3900
MAX_PHOTO_CAPTION_LENGTH = 1000
MAX_STATE_ITEMS = 10000

DEFAULT_MAX_POSTS_PER_RUN = 60
DEFAULT_MAX_POSTS_FROM_CHANNEL = 2

MIN_CLEAN_TEXT_LENGTH = 25

MILITARY_COLLECTOR_VERSION = "2026-07-31-photo-multipart-v1"


# Фразы, после которых весь оставшийся текст считается
# рекламным или служебным хвостом.
TAIL_CUTOFF_PHRASES = (
    "поддержать нас",
    "поддержите нас",
    "поддержать проект",
    "поддержать канал",
    "помочь проекту",
    "помочь каналу",
    "для переводов из-за рубежа",
    "для переводов из за рубежа",
    "для переводов",
    "реквизиты для помощи",
    "реквизиты для перевода",
    "реквизиты для поддержки",
    "все подробности о сборах",
    "подробности о сборах",
    "отчеты о сборах",
    "отчёты о сборах",
    "сборы и отчеты",
    "сборы и отчёты",
    "карта в высоком разрешении",
    "карты в высоком разрешении",
    "онлайн-карты доступны",
    "онлайн карты доступны",
    "english version",
    "версия на английском",
    "написать нам в бот обратной связи",
    "бот обратной связи",
    "обратная связь",
    "предложить новость",
    "прислать новость",
    "по вопросам рекламы",
    "реклама и сотрудничество",
    "разместить рекламу",
    "наши социальные сети",
    "мы в социальных сетях",
    "следите за нами",
    "подписывайтесь на нас",
    "подпишитесь на нас",
)


# Фразы, при наличии которых удаляется только конкретная строка.
PROMO_PHRASES = (
    "не грузит фото и видео",
    "переходи в наш max",
    "переходите в наш max",
    "переходи в max",
    "переходите в max",
    "подписывайтесь на наш канал",
    "подпишитесь на наш канал",
    "подписаться на канал",
    "подписаться",
    "наш telegram-канал",
    "наш телеграм-канал",
    "наш telegram канал",
    "наш телеграм канал",
    "наш канал",
    "наш чат",
    "наш бот",
    "наше приложение",
    "скачать приложение",
    "курс на макс",
    "ос в max",
    "ос в макс",
    "мы в max",
    "мы в макс",
    "читайте нас в max",
    "читайте нас в макс",
    "присоединяйтесь к нам",
    "подпишись на",
    "подпишитесь на",
)


TELEGRAM_LINK_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?"
    r"(?:t\.me|telegram\.me)/[^\s<>]+",
    flags=re.IGNORECASE,
)

GENERAL_URL_PATTERN = re.compile(
    r"(?:https?://|www\.)[^\s<>]+",
    flags=re.IGNORECASE,
)

MARKDOWN_LINK_PATTERN = re.compile(
    r"\[([^\]]+)]\("
    r"(?:https?://)?(?:www\.)?"
    r"(?:t\.me|telegram\.me)/[^)]+\)",
    flags=re.IGNORECASE,
)

USERNAME_PATTERN = re.compile(
    r"(?<![\w@])@[A-Za-z0-9_]{4,}",
)

HASHTAG_PATTERN = re.compile(
    r"(?<!\w)#[A-Za-zА-Яа-яЁёІіЇїЄє0-9_]+",
)

PHONE_PATTERN = re.compile(
    r"(?:\+?\d[\d\s()\-]{8,}\d)"
)

LONG_NUMBER_PATTERN = re.compile(
    r"(?<!\d)\d{12,20}(?!\d)"
)

CARD_GROUP_PATTERN = re.compile(
    r"(?<!\d)(?:\d{4}[\s\-]?){3}\d{4}(?!\d)"
)

CRYPTO_ADDRESS_PATTERN = re.compile(
    r"\b(?:"
    r"bc1[a-zA-HJ-NP-Z0-9]{20,}|"
    r"[13][a-km-zA-HJ-NP-Z1-9]{25,34}|"
    r"0x[a-fA-F0-9]{40}|"
    r"4[0-9AB][1-9A-HJ-NP-Za-km-z]{90,110}"
    r")\b"
)

REPEATED_EMPTY_LINES_PATTERN = re.compile(
    r"\n{3,}"
)

ONLY_PUNCTUATION_PATTERN = re.compile(
    r"^[\s\-—–_=+|•·▪▫●○■□◆◇"
    r"📌📍📢📣🔔➡️👉👆👇✅❗❕"
    r"💬📱✉️⭐⚠️🎯✈️🚀🇷🇺🇺🇦"
    r"⬛◾🔹🔸]+$"
)

SOCIAL_SERVICE_PATTERN = re.compile(
    r"^(?:"
    r"vk|вк|"
    r"max|макс|"
    r"дзен|dzen|"
    r"rutube|рутуб|"
    r"youtube|ютуб|"
    r"telegram|телеграм|"
    r"ok|одноклассники|"
    r"ru|en|"
    r"сайт|website|"
    r"канал|чат|бот"
    r")"
    r"(?:\s*[:\-—–|•]*)?$",
    flags=re.IGNORECASE,
)

PAYMENT_SERVICE_PATTERN = re.compile(
    r"^(?:"
    r"сбер|сбербанк|"
    r"рнкб|альфа|альфа-банк|"
    r"тинькофф|т-банк|"
    r"сбп|"
    r"втб|газпромбанк|"
    r"bitcoin|btc|"
    r"ethereum|eth|"
    r"monero|xmr|"
    r"криптовалюта|криптокошелёк|"
    r"криптокошелек"
    r")"
    r"(?:\s*[:\-—–|•]*)?$",
    flags=re.IGNORECASE,
)


def load_lines(path: Path) -> list[str]:
    """Читает строки файла, пропуская комментарии и пустые строки."""
    if not path.exists():
        print(f"Файл не найден: {path}")
        return []

    result: list[str] = []

    for raw_line in path.read_text(
        encoding="utf-8",
    ).splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        line = re.sub(
            r"^https?://(?:www\.)?t\.me/",
            "",
            line,
            flags=re.IGNORECASE,
        )

        line = line.removeprefix("@")
        line = line.strip("/ ")

        if line:
            result.append(line)

    return list(dict.fromkeys(result))


def load_config(path: Path) -> dict[str, Any]:
    """Загружает и проверяет настройки тематического канала."""
    if not path.exists():
        raise FileNotFoundError(
            f"Файл конфигурации не найден: {path}"
        )

    raw_config = json.loads(
        path.read_text(encoding="utf-8")
    )

    target_channel = str(
        raw_config.get("target_channel", "")
    ).strip()

    news_radar_channel = str(
        raw_config.get("news_radar_channel", "")
    ).strip()

    posts_per_channel = int(
        raw_config.get("posts_per_channel", 10)
    )

    max_posts_per_run = int(
        raw_config.get(
            "max_posts_per_run",
            DEFAULT_MAX_POSTS_PER_RUN,
        )
    )

    max_posts_from_channel = int(
        raw_config.get(
            "max_posts_from_channel",
            DEFAULT_MAX_POSTS_FROM_CHANNEL,
        )
    )

    if not target_channel:
        raise ValueError(
            "В config.json не указан target_channel."
        )

    if posts_per_channel < 1:
        raise ValueError(
            "posts_per_channel должен быть больше нуля."
        )

    if max_posts_per_run < 1:
        raise ValueError(
            "max_posts_per_run должен быть больше нуля."
        )

    if max_posts_from_channel < 1:
        raise ValueError(
            "max_posts_from_channel должен быть больше нуля."
        )

    return {
        "target_channel": target_channel,
        "news_radar_channel": news_radar_channel,
        "posts_per_channel": posts_per_channel,
        "max_posts_per_run": max_posts_per_run,
        "max_posts_from_channel": max_posts_from_channel,
    }


def make_post_key(post: TelegramPost) -> str:
    """Создаёт уникальный ключ сообщения с учётом канала."""
    channel = str(post.channel).strip().lower()
    return f"{channel}:{int(post.message_id)}"


def load_state(path: Path) -> tuple[set[str], set[int]]:
    """Загружает новое и старое состояние публикаций."""
    if not path.exists():
        return set(), set()

    try:
        raw_state = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as error:
        print(f"Не удалось прочитать state.json: {error}")
        return set(), set()

    published_keys: set[str] = set()
    legacy_message_ids: set[int] = set()

    raw_keys = raw_state.get(
        "published_post_keys",
        [],
    )

    if isinstance(raw_keys, list):
        for raw_key in raw_keys:
            key = str(raw_key).strip().lower()

            if key:
                published_keys.add(key)

    raw_legacy_ids = raw_state.get(
        "published_message_ids",
        [],
    )

    if isinstance(raw_legacy_ids, list):
        for raw_id in raw_legacy_ids:
            try:
                legacy_message_ids.add(int(raw_id))
            except (TypeError, ValueError):
                continue

    return published_keys, legacy_message_ids


def save_state( path: Path, published_keys: set[str], legacy_message_ids: set[int], ) -> None:
    """Сохраняет состояние атомарно."""
    limited_keys = sorted(
        published_keys
    )[-MAX_STATE_ITEMS:]

    limited_legacy_ids = sorted(
        legacy_message_ids
    )[-MAX_STATE_ITEMS:]

    state = {
        "published_post_keys": limited_keys,
        "published_message_ids": limited_legacy_ids,
    }

    temporary_path = path.with_suffix(".tmp")

    temporary_path.write_text(
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary_path.replace(path)


def get_bot_token() -> str:
    """Получает токен Telegram-бота."""
    possible_names = (
        "BOT_TOKEN",
        "TELEGRAM_BOT_TOKEN",
        "NEWS_BOT_TOKEN",
    )

    for variable_name in possible_names:
        token = os.getenv(
            variable_name,
            "",
        ).strip()

        if token:
            print(
                "Токен Telegram найден в переменной: "
                f"{variable_name}"
            )
            return token

    return ""


def normalize_for_check(text: str) -> str:
    """Нормализует строку для проверки на мусор."""
    normalized = html.unescape(
        text or ""
    )

    normalized = normalized.replace(
        "\u00a0",
        " ",
    )

    normalized = normalized.replace(
        "\u200b",
        "",
    )

    normalized = normalized.lower()

    normalized = re.sub(
        r"[«»\"'`]+",
        "",
        normalized,
    )

    normalized = re.sub(
        r"^[^\wа-яё]+",
        "",
        normalized,
        flags=re.IGNORECASE,
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )

    return normalized.strip(" .,:;!?—–-|")


def is_tail_cutoff_line(line: str) -> bool:
    """Проверяет, начинается ли рекламный хвост."""
    normalized = normalize_for_check(line)

    if not normalized:
        return False

    for phrase in TAIL_CUTOFF_PHRASES:
        if (
            normalized == phrase
            or normalized.startswith(phrase + " ")
            or normalized.startswith(phrase + ":")
        ):
            return True

    return False


def is_payment_line(line: str) -> bool:
    """Определяет строки с реквизитами и донатами."""
    normalized = normalize_for_check(line)

    if not normalized:
        return False

    if PAYMENT_SERVICE_PATTERN.fullmatch(normalized):
        return True

    payment_words = (
        "номер карты",
        "карта сбер",
        "карта рнкб",
        "карта альфа",
        "карта втб",
        "по номеру телефона",
        "по номеру тлф",
        "по номеру тел",
        "по номеру карты",
        "для перевода",
        "для доната",
        "для пожертвований",
        "кошелек btc",
        "кошелёк btc",
        "криптокошелек",
        "криптокошелёк",
    )

    if any(
        phrase in normalized
        for phrase in payment_words
    ):
        return True

    if CARD_GROUP_PATTERN.search(line):
        return True

    if LONG_NUMBER_PATTERN.search(line):
        return True

    if CRYPTO_ADDRESS_PATTERN.search(line):
        return True

    if (
        PHONE_PATTERN.search(line)
        and any(
            word in normalized
            for word in (
                "сбер",
                "сбп",
                "перевод",
                "телефон",
                "тлф",
                "карта",
                "донат",
            )
        )
    ):
        return True

    return False


def is_social_service_line(line: str) -> bool:
    """Удаляет отдельные строки с названиями социальных сетей."""
    normalized = normalize_for_check(line)

    if not normalized:
        return False

    return bool(
        SOCIAL_SERVICE_PATTERN.fullmatch(normalized)
    )


def is_promotional_line(line: str) -> bool:
    """Определяет рекламную или служебную строку."""
    normalized = normalize_for_check(line)

    if not normalized:
        return False

    if any(
        phrase in normalized
        for phrase in PROMO_PHRASES
    ):
        return True

    if is_payment_line(line):
        return True

    if is_social_service_line(line):
        return True

    if ONLY_PUNCTUATION_PATTERN.fullmatch(line.strip()):
        return True

    if USERNAME_PATTERN.fullmatch(line.strip()):
        return True

    without_hashtags = HASHTAG_PATTERN.sub(
        "",
        line,
    ).strip()

    if (
        HASHTAG_PATTERN.search(line)
        and not without_hashtags
    ):
        return True

    if GENERAL_URL_PATTERN.fullmatch(line.strip()):
        return True

    if TELEGRAM_LINK_PATTERN.fullmatch(line.strip()):
        return True

    if (
        TELEGRAM_LINK_PATTERN.search(line)
        and any(
            word in normalized
            for word in (
                "подпис",
                "канал",
                "чат",
                "бот",
                "новости",
            )
        )
    ):
        return True

    return False


def clean_inline_garbage(line: str) -> str:
    """Удаляет ссылки, хештеги и упоминания внутри полезной строки."""
    cleaned = line

    cleaned = MARKDOWN_LINK_PATTERN.sub(
        r"\1",
        cleaned,
    )

    cleaned = TELEGRAM_LINK_PATTERN.sub(
        "",
        cleaned,
    )

    cleaned = GENERAL_URL_PATTERN.sub(
        "",
        cleaned,
    )

    cleaned = USERNAME_PATTERN.sub(
        "",
        cleaned,
    )

    cleaned = HASHTAG_PATTERN.sub(
        "",
        cleaned,
    )

    cleaned = CARD_GROUP_PATTERN.sub(
        "",
        cleaned,
    )

    cleaned = CRYPTO_ADDRESS_PATTERN.sub(
        "",
        cleaned,
    )

    cleaned = re.sub(
        r"\s+",
        " ",
        cleaned,
    ).strip()

    cleaned = re.sub(
        r"^[|•·▪▫—–\-_=]+\s*",
        "",
        cleaned,
    ).strip()

    cleaned = re.sub(
        r"\s*[|•·▪▫—–\-_=]+$",
        "",
        cleaned,
    ).strip()

    return cleaned


def clean_post_text(raw_text: str) -> str:
    """Агрессивно очищает Telegram-публикацию."""
    text = html.unescape(
        raw_text or ""
    )

    text = text.replace(
        "\u00a0",
        " ",
    )

    text = text.replace(
        "\u200b",
        "",
    )

    text = text.replace(
        "\r\n",
        "\n",
    )

    text = text.replace(
        "\r",
        "\n",
    )

    raw_lines = text.splitlines()
    cleaned_lines: list[str] = []

    for raw_line in raw_lines:
        line = raw_line.strip()

        # Если начался рекламный хвост,
        # отбрасываем его вместе со всем последующим текстом.
        if line and is_tail_cutoff_line(line):
            print(
                "Обрезан рекламный хвост начиная со строки: "
                f"{line[:80]}"
            )
            break

        if not line:
            if (
                cleaned_lines
                and cleaned_lines[-1] != ""
            ):
                cleaned_lines.append("")
            continue

        if is_promotional_line(line):
            continue

        line = clean_inline_garbage(line)

        if not line:
            continue

        if is_promotional_line(line):
            continue

        # Удаляем короткие остатки вроде:
        # "MAX", "VK", "RU", "EN", "Сбер".
        if (
            len(line) <= 20
            and (
                is_social_service_line(line)
                or is_payment_line(line)
            )
        ):
            continue

        cleaned_lines.append(line)

    # Убираем пустоту в начале и конце.
    while (
        cleaned_lines
        and cleaned_lines[0] == ""
    ):
        cleaned_lines.pop(0)

    while (
        cleaned_lines
        and cleaned_lines[-1] == ""
    ):
        cleaned_lines.pop()

    # Удаляем повторяющиеся пустые строки.
    compact_lines: list[str] = []

    for line in cleaned_lines:
        if (
            line == ""
            and (
                not compact_lines
                or compact_lines[-1] == ""
            )
        ):
            continue

        compact_lines.append(line)

    cleaned_text = "\n".join(
        compact_lines
    )

    cleaned_text = REPEATED_EMPTY_LINES_PATTERN.sub(
        "\n\n",
        cleaned_text,
    )

    cleaned_text = re.sub(
        r"[ \t]+\n",
        "\n",
        cleaned_text,
    )

    cleaned_text = re.sub(
        r"\n[ \t]+",
        "\n",
        cleaned_text,
    )

    cleaned_text = re.sub(
        r" +([.,!?;:])",
        r"\1",
        cleaned_text,
    )

    cleaned_text = re.sub(
        r"([,;:]){2,}",
        r"\1",
        cleaned_text,
    )

    cleaned_text = re.sub(
        r"\n[.,;:!?—–\-]+\n",
        "\n",
        cleaned_text,
    )

    return cleaned_text.strip()


def format_post(post: TelegramPost) -> str:
    """Формирует очищенную публикацию."""
    source_name = f"@{post.channel}"
    text = clean_post_text(post.text)

    if len(text) > MAX_MESSAGE_LENGTH:
        text = (
            text[:MAX_MESSAGE_LENGTH].rstrip()
            + "…"
        )

    return (
        f"{html.escape(text)}\n\n"
        f"Источник: "
        f'<a href="{html.escape(post.source_url)}">'
        f"{html.escape(source_name)}</a>"
    )


def _detect_image_type(image_data: bytes) -> tuple[str, str]:
    """Определяет MIME-тип и расширение изображения по сигнатуре файла."""
    if image_data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "jpg"

    if image_data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "png"

    if image_data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif", "gif"

    if (
        len(image_data) >= 12
        and image_data[:4] == b"RIFF"
        and image_data[8:12] == b"WEBP"
    ):
        return "image/webp", "webp"

    return "", ""


def download_post_image( image_url: str, source_url: str, ) -> tuple[bytes, str, str] | None:
    """Скачивает изображение самостоятельно перед отправкой в Telegram."""
    normalized_url = html.unescape(
        str(image_url or "").strip()
    ).replace("\\/", "/")

    if normalized_url.startswith("//"):
        normalized_url = "https:" + normalized_url

    if not normalized_url.startswith(("http://", "https://")):
        print(
            "Некорректная ссылка на фотографию: "
            f"{normalized_url[:200]}"
        )
        return None

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 13) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        ),
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,"
        "image/*,*/*;q=0.8",
        "Accept-Language": "ru,en;q=0.8",
        "Referer": source_url,
    }

    try:
        response = requests.get(
            normalized_url,
            timeout=TELEGRAM_TIMEOUT,
            headers=headers,
            allow_redirects=True,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        print(
            "Не удалось скачать фотографию: "
            f"{error}; URL: {normalized_url[:200]}"
        )
        return None

    image_data = response.content

    if not image_data:
        print(
            "Сервер вернул пустую фотографию: "
            f"{normalized_url[:200]}"
        )
        return None

    detected_mime, extension = _detect_image_type(image_data)
    response_mime = response.headers.get(
        "Content-Type",
        "",
    ).split(";", 1)[0].strip().lower()

    if not detected_mime:
        print(
            "Загруженный файл не похож на изображение: "
            f"Content-Type={response_mime or 'не указан'}; "
            f"URL: {normalized_url[:200]}"
        )
        return None

    filename = f"telegram_photo.{extension}"

    print(
        "Фотография скачана: "
        f"{len(image_data)} байт; "
        f"{detected_mime}; "
        f"{source_url}"
    )

    return image_data, detected_mime, filename


def publish_post( token: str, target_channel: str, post: TelegramPost, ) -> bool:
    """Публикует пост с загруженной фотографией или резервным текстом."""
    cleaned_text = clean_post_text(post.text)

    if len(cleaned_text) < MIN_CLEAN_TEXT_LENGTH:
        print(
            "Сообщение пропущено после очистки: "
            f"{post.source_url}"
        )
        return False

    source_name = f"@{post.channel}"

    source_html = (
        f"Источник: "
        f'<a href="{html.escape(post.source_url)}">'
        f"{html.escape(source_name)}</a>"
    )

    if post.image_url:
        caption_space = (
            MAX_PHOTO_CAPTION_LENGTH
            - len(source_html)
            - 3
        )

        caption_text = cleaned_text

        if len(caption_text) > caption_space:
            caption_text = (
                caption_text[:caption_space].rstrip()
                + "…"
            )

        caption = (
            f"{html.escape(caption_text)}\n\n"
            f"{source_html}"
        )

        downloaded_image = download_post_image(
            image_url=post.image_url,
            source_url=post.source_url,
        )

        if downloaded_image is not None:
            image_data, image_mime, filename = downloaded_image

            photo_api_url = (
                "https://api.telegram.org/"
                f"bot{token}/sendPhoto"
            )

            try:
                photo_response = requests.post(
                    photo_api_url,
                    timeout=TELEGRAM_TIMEOUT,
                    data={
                        "chat_id": target_channel,
                        "caption": caption,
                        "parse_mode": "HTML",
                    },
                    files={
                        "photo": (
                            filename,
                            image_data,
                            image_mime,
                        ),
                    },
                )

                if photo_response.ok:
                    print(
                        "Опубликовано с фотографией: "
                        f"{post.source_url} -> "
                        f"{target_channel}"
                    )
                    return True

                print(
                    "Telegram отклонил загруженную фотографию, "
                    "пробуем отправить текст: "
                    f"HTTP {photo_response.status_code}; "
                    f"{photo_response.text}"
                )

            except requests.RequestException as error:
                print(
                    "Ошибка загрузки фотографии в Telegram, "
                    f"пробуем отправить текст: {error}"
                )

    message_api_url = (
        "https://api.telegram.org/"
        f"bot{token}/sendMessage"
    )

    try:
        message_response = requests.post(
            message_api_url,
            timeout=TELEGRAM_TIMEOUT,
            data={
                "chat_id": target_channel,
                "text": format_post(post),
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )
    except requests.RequestException as error:
        print(
            "Ошибка текстовой публикации: "
            f"{error}"
        )
        return False

    if message_response.ok:
        print(
            f"Опубликовано текстом: {post.source_url}"
        )
        return True

    print(
        "Ошибка публикации: "
        f"HTTP {message_response.status_code}; "
        f"{message_response.text}"
    )

    return False

def select_new_posts( posts: list[TelegramPost], military_filter: MilitaryFilter, published_keys: set[str], legacy_message_ids: set[int], ) -> list[TelegramPost]:
    """Оставляет новые сообщения, прошедшие фильтр и очистку."""
    selected: list[TelegramPost] = []
    current_run_keys: set[str] = set()

    use_legacy_ids = not published_keys

    for post in posts:
        post_key = make_post_key(post)

        if post_key in published_keys:
            continue

        if post_key in current_run_keys:
            continue

        if (
            use_legacy_ids
            and post.message_id in legacy_message_ids
        ):
            continue

        current_run_keys.add(post_key)

        if not military_filter.check(post):
            continue

        cleaned_text = clean_post_text(post.text)

        if len(cleaned_text) < MIN_CLEAN_TEXT_LENGTH:
            print(
                "Сообщение отклонено после очистки: "
                f"{post.source_url}"
            )
            continue

        selected.append(post)

    return selected


def distribute_posts_round_robin( posts: list[TelegramPost], channels: list[str], max_posts_from_channel: int, max_posts_per_run: int, ) -> list[TelegramPost]:
    """Распределяет публикации равномерно между источниками."""
    grouped_posts: dict[
        str,
        list[TelegramPost],
    ] = defaultdict(list)

    for post in posts:
        channel_key = str(
            post.channel
        ).strip().lower()

        grouped_posts[channel_key].append(post)

    for channel_posts in grouped_posts.values():
        channel_posts.sort(
            key=lambda post: int(post.message_id),
            reverse=True,
        )

        del channel_posts[max_posts_from_channel:]

    channel_order: list[str] = []

    for channel in channels:
        channel_key = channel.strip().lower()

        if (
            channel_key in grouped_posts
            and channel_key not in channel_order
        ):
            channel_order.append(channel_key)

    for channel_key in grouped_posts:
        if channel_key not in channel_order:
            channel_order.append(channel_key)

    distributed: list[TelegramPost] = []

    for position in range(max_posts_from_channel):
        for channel_key in channel_order:
            channel_posts = grouped_posts[channel_key]

            if position >= len(channel_posts):
                continue

            distributed.append(
                channel_posts[position]
            )

            if len(distributed) >= max_posts_per_run:
                return distributed

    return distributed


def main() -> None:
    """Запускает тематический Telegram-конвейер."""
    print("Запуск Telegram Military Collector.")
    print(f"Версия collector: {MILITARY_COLLECTOR_VERSION}")

    try:
        config = load_config(CONFIG_FILE)
    except Exception as error:
        print(f"Ошибка конфигурации: {error}")
        return

    channels = load_lines(CHANNELS_FILE)

    if not channels:
        print("В channels.txt нет Telegram-каналов.")
        return

    token = get_bot_token()

    if not token:
        print(
            "Токен Telegram-бота не найден. "
            "Проверьте секрет BOT_TOKEN."
        )
        return

    target_channel = str(
        config["target_channel"]
    )

    news_radar_channel = str(
        config["news_radar_channel"]
    )

    posts_per_channel = int(
        config["posts_per_channel"]
    )

    max_posts_per_run = int(
        config["max_posts_per_run"]
    )

    max_posts_from_channel = int(
        config["max_posts_from_channel"]
    )

    published_keys, legacy_message_ids = load_state(
        STATE_FILE
    )

    print(f"Целевой канал: {target_channel}")
    print(
        "Дополнительный канал News Radar: "
        f"{news_radar_channel}"
    )
    print(f"Источников: {len(channels)}")

    print(
        "Ранее опубликованных уникальных ключей: "
        f"{len(published_keys)}"
    )

    print(
        "Максимум с одного источника: "
        f"{max_posts_from_channel}"
    )

    print(
        "Общий максимум за запуск: "
        f"{max_posts_per_run}"
    )

    parser = TelegramPublicParser(
        posts_per_channel=posts_per_channel,
    )

    military_filter = MilitaryFilter(
        topic_dir=str(TOPIC_DIR),
    )

    posts = parser.fetch_channels(channels)

    if not posts:
        print("Парсер не получил публикаций.")
        return

    print(
        f"Всего получено публикаций: {len(posts)}"
    )

    selected_posts = select_new_posts(
        posts=posts,
        military_filter=military_filter,
        published_keys=published_keys,
        legacy_message_ids=legacy_message_ids,
    )

    print(
        "Новых публикаций после фильтра и очистки: "
        f"{len(selected_posts)}"
    )

    posts_to_publish = distribute_posts_round_robin(
        posts=selected_posts,
        channels=channels,
        max_posts_from_channel=max_posts_from_channel,
        max_posts_per_run=max_posts_per_run,
    )

    print(
        "Подготовлено к публикации: "
        f"{len(posts_to_publish)}"
    )

    published_count = 0

    published_by_channel: dict[
        str,
        int,
    ] = defaultdict(int)

    for post in posts_to_publish:
        try:
            success = publish_post(
                token=token,
                target_channel=target_channel,
                post=post,
            )
        except Exception as error:
            print(
                f"Ошибка отправки {post.source_url}: "
                f"{error}"
            )
            continue

        if not success:
            continue

        try:
            news_radar_success = publish_post(
                token=token,
                target_channel=news_radar_channel,
                post=post,
            )
        except Exception as error:
            print(
                "Ошибка отправки в News Radar "
                f"{post.source_url}: {error}"
            )
            news_radar_success = False

        if not news_radar_success:
            print(
                "Публикация отправлена в военный канал, "
                "но не отправлена в News Radar. "
                "Она не будет записана в state.json и "
                "будет повторена при следующем запуске."
            )
            continue

        print(
            "Публикация отправлена в оба канала: "
            f"{post.source_url}"
        )

        post_key = make_post_key(post)
        published_keys.add(post_key)

        channel_name = str(
            post.channel
        ).strip()

        published_by_channel[channel_name] += 1
        published_count += 1

        try:
            save_state(
                path=STATE_FILE,
                published_keys=published_keys,
                legacy_message_ids=legacy_message_ids,
            )
        except OSError as error:
            print(
                "Сообщение опубликовано, но состояние "
                f"не сохранено: {error}"
            )
            return

    if published_by_channel:
        print("Распределение публикаций:")

        for channel_name, count in (
            published_by_channel.items()
        ):
            print(
                f" @{channel_name}: {count}"
            )

    print(
        "Работа завершена. "
        f"Опубликовано сообщений: {published_count}"
    )


if __name__ == "__main__":
    main()
