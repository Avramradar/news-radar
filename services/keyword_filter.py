import json
from pathlib import Path
from typing import Any


CONFIG_PATH = (
    Path(__file__).resolve().parent.parent
    / "filters"
    / "telegram_news_filters.json"
)


def load_telegram_filters() -> dict[str, Any]:
    """
    Загружает настройки фильтрации Telegram-каналов.

    Если файл отсутствует, повреждён или имеет неправильную структуру,
    возвращает безопасную пустую конфигурацию.
    """
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as file:
            config = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"channels": {}}

    if not isinstance(config, dict):
        return {"channels": {}}

    channels = config.get("channels")

    if not isinstance(channels, dict):
        return {"channels": {}}

    return {"channels": channels}


def normalize_channel_name(channel_name: str) -> str:
    """
    Приводит имя или ссылку Telegram-канала к единому виду.

    Примеры:
    @example_channel -> example_channel
    https://t.me/example_channel -> example_channel
    example_channel -> example_channel
    """
    normalized = str(channel_name or "").strip()

    for prefix in (
        "https://t.me/",
        "http://t.me/",
        "https://telegram.me/",
        "http://telegram.me/",
    ):
        if normalized.lower().startswith(prefix):
            normalized = normalized[len(prefix):]
            break

    normalized = normalized.lstrip("@").strip("/")
    return normalized.lower()


def normalize_text(text: str) -> str:
    """
    Подготавливает текст к регистронезависимому поиску.
    """
    return " ".join(str(text or "").lower().split())


def get_channel_rules(
    channel_name: str,
    config: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    Возвращает правила конкретного канала.

    Если канал отсутствует в конфигурации, возвращает None.
    """
    if config is None:
        config = load_telegram_filters()

    channels = config.get("channels", {})
    normalized_channel = normalize_channel_name(channel_name)

    for configured_channel, rules in channels.items():
        if normalize_channel_name(configured_channel) == normalized_channel:
            if isinstance(rules, dict):
                return rules
            return None

    return None


def should_publish_telegram_post(
    channel_name: str,
    text: str,
    config: dict[str, Any] | None = None,
) -> bool:
    """
    Проверяет, разрешено ли публиковать сообщение Telegram-канала.

    Правила:
    1. Канал должен быть явно указан в конфигурации.
    2. Канал должен быть включён.
    3. При совпадении с exclude_keywords сообщение блокируется.
    4. Должно совпасть хотя бы одно слово из include_keywords.
    """
    rules = get_channel_rules(channel_name, config)

    if rules is None:
        return False

    if rules.get("enabled", True) is not True:
        return False

    normalized_post = normalize_text(text)

    if not normalized_post:
        return False

    exclude_keywords = rules.get("exclude_keywords", [])
    if not isinstance(exclude_keywords, list):
        exclude_keywords = []

    for keyword in exclude_keywords:
        normalized_keyword = normalize_text(keyword)

        if normalized_keyword and normalized_keyword in normalized_post:
            return False

    include_keywords = rules.get("include_keywords", [])
    if not isinstance(include_keywords, list):
        return False

    for keyword in include_keywords:
        normalized_keyword = normalize_text(keyword)

        if normalized_keyword and normalized_keyword in normalized_post:
            return True

    return False
