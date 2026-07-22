from __future__ import annotations

import os
import re
import time
from typing import Any

import requests


BOT_TOKEN = os.environ["BOT_TOKEN"]

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Пользователи, от которых бот ожидает список продуктов.
WAITING_FOR_INGREDIENTS: set[int] = set()


# Разные названия одного продукта приводим к единой форме.
INGREDIENT_ALIASES = {
    "картошка": "картофель",
    "картошку": "картофель",
    "картошки": "картофель",
    "картофеля": "картофель",

    "помидор": "помидоры",
    "помидора": "помидоры",
    "помидоры": "помидоры",
    "томат": "помидоры",
    "томаты": "помидоры",

    "огурец": "огурцы",
    "огурца": "огурцы",
    "огурцы": "огурцы",

    "яйцо": "яйца",
    "яйца": "яйца",
    "яиц": "яйца",

    "луковица": "лук",
    "лука": "лук",
    "репчатый лук": "лук",

    "морковка": "морковь",
    "моркови": "морковь",

    "курица": "курица",
    "курицу": "курица",
    "курицы": "курица",
    "куриное филе": "курица",
    "филе курицы": "курица",
    "грудка": "курица",
    "куриная грудка": "курица",

    "фарша": "фарш",
    "мясной фарш": "фарш",

    "сыра": "сыр",
    "твердый сыр": "сыр",
    "твёрдый сыр": "сыр",

    "молока": "молоко",
    "сметаны": "сметана",
    "кефира": "кефир",
    "творога": "творог",

    "макарон": "макароны",
    "макароны": "макароны",
    "паста": "макароны",
    "спагетти": "макароны",

    "риса": "рис",
    "гречки": "гречка",

    "капусты": "капуста",
    "белокочанная капуста": "капуста",

    "гриб": "грибы",
    "гриба": "грибы",
    "грибы": "грибы",
    "шампиньон": "грибы",
    "шампиньоны": "грибы",

    "колбасы": "колбаса",
    "сосиска": "сосиски",
    "сосиски": "сосиски",

    "хлеба": "хлеб",
    "батон": "хлеб",

    "муки": "мука",
    "масла": "масло",
    "растительное масло": "масло",
    "подсолнечное масло": "масло",

    "чеснока": "чеснок",
    "перца": "перец",
}


# Соль, вода, масло и базовые специи считаются продуктами,
# которые обычно уже есть дома.
BASIC_PRODUCTS = {
    "соль",
    "перец",
    "вода",
    "масло",
    "специи",
    "сахар",
}


RECIPES = [
    {
        "name": "Картофельная запеканка с сыром",
        "ingredients": {
            "картофель",
            "сыр",
            "лук",
            "сметана",
            "масло",
        },
        "instructions": (
            "Нарежьте картофель тонкими ломтиками. "
            "Выложите слоями с луком, смажьте сметаной "
            "и посыпьте сыром. Запекайте 35–45 минут "
            "при 180 °C."
        ),
    },
    {
        "name": "Драники",
        "ingredients": {
            "картофель",
            "яйца",
            "лук",
            "мука",
            "масло",
            "соль",
        },
        "instructions": (
            "Натрите картофель и лук, добавьте яйцо, "
            "муку и соль. Перемешайте и обжарьте "
            "небольшими порциями до золотистой корочки."
        ),
    },
    {
        "name": "Омлет с сыром",
        "ingredients": {
            "яйца",
            "сыр",
            "молоко",
            "масло",
            "соль",
        },
        "instructions": (
            "Взбейте яйца с молоком и солью. "
            "Вылейте на сковороду, добавьте тёртый сыр "
            "и готовьте под крышкой 5–7 минут."
        ),
    },
    {
        "name": "Омлет с помидорами",
        "ingredients": {
            "яйца",
            "помидоры",
            "лук",
            "масло",
            "соль",
        },
        "instructions": (
            "Обжарьте лук и помидоры. Залейте взбитыми "
            "яйцами, посолите и готовьте под крышкой "
            "до схватывания."
        ),
    },
    {
        "name": "Жареный картофель с грибами",
        "ingredients": {
            "картофель",
            "грибы",
            "лук",
            "масло",
            "соль",
        },
        "instructions": (
            "Отдельно обжарьте грибы с луком. "
            "Картофель жарьте до румяности, затем "
            "соедините с грибами и доведите до готовности."
        ),
    },
    {
        "name": "Курица с картофелем в духовке",
        "ingredients": {
            "курица",
            "картофель",
            "лук",
            "чеснок",
            "масло",
            "соль",
            "специи",
        },
        "instructions": (
            "Нарежьте курицу и картофель, добавьте лук, "
            "чеснок, масло и специи. Перемешайте и "
            "запекайте 45–55 минут при 190 °C."
        ),
    },
    {
        "name": "Курица в сметанном соусе",
        "ingredients": {
            "курица",
            "сметана",
            "лук",
            "чеснок",
            "масло",
            "соль",
        },
        "instructions": (
            "Обжарьте кусочки курицы с луком. Добавьте "
            "сметану, немного воды и чеснок. Тушите "
            "под крышкой около 20 минут."
        ),
    },
    {
        "name": "Макароны с сыром",
        "ingredients": {
            "макароны",
            "сыр",
            "масло",
            "соль",
        },
        "instructions": (
            "Отварите макароны до готовности. "
            "Добавьте масло и тёртый сыр, перемешайте "
            "до расплавления сыра."
        ),
    },
    {
        "name": "Макароны с фаршем",
        "ingredients": {
            "макароны",
            "фарш",
            "лук",
            "помидоры",
            "масло",
            "соль",
        },
        "instructions": (
            "Обжарьте фарш с луком. Добавьте помидоры "
            "или томатную основу, потушите 10 минут "
            "и смешайте с отваренными макаронами."
        ),
    },
    {
        "name": "Рис с курицей",
        "ingredients": {
            "рис",
            "курица",
            "лук",
            "морковь",
            "масло",
            "соль",
            "специи",
        },
        "instructions": (
            "Обжарьте курицу, лук и морковь. Добавьте "
            "промытый рис и воду в пропорции примерно "
            "один к двум. Готовьте под крышкой до мягкости."
        ),
    },
    {
        "name": "Гречка с грибами",
        "ingredients": {
            "гречка",
            "грибы",
            "лук",
            "масло",
            "соль",
        },
        "instructions": (
            "Отварите гречку. Обжарьте грибы с луком, "
            "смешайте с готовой крупой и прогрейте "
            "несколько минут."
        ),
    },
    {
        "name": "Тушёная капуста",
        "ingredients": {
            "капуста",
            "морковь",
            "лук",
            "помидоры",
            "масло",
            "соль",
        },
        "instructions": (
            "Обжарьте лук и морковь, добавьте нашинкованную "
            "капусту и помидоры. Тушите под крышкой "
            "30–40 минут, периодически перемешивая."
        ),
    },
    {
        "name": "Салат из помидоров и огурцов",
        "ingredients": {
            "помидоры",
            "огурцы",
            "лук",
            "масло",
            "соль",
        },
        "instructions": (
            "Нарежьте овощи, добавьте лук, соль и масло. "
            "Перемешивайте непосредственно перед подачей."
        ),
    },
    {
        "name": "Горячие бутерброды",
        "ingredients": {
            "хлеб",
            "сыр",
            "колбаса",
            "помидоры",
        },
        "instructions": (
            "На хлеб выложите колбасу, помидоры и сыр. "
            "Запекайте 7–10 минут при 190 °C или готовьте "
            "на сковороде под крышкой."
        ),
    },
    {
        "name": "Сырники",
        "ingredients": {
            "творог",
            "яйца",
            "мука",
            "сахар",
            "масло",
        },
        "instructions": (
            "Смешайте творог с яйцом, сахаром и мукой. "
            "Сформируйте небольшие сырники и обжарьте "
            "с двух сторон на умеренном огне."
        ),
    },
    {
        "name": "Оладьи на кефире",
        "ingredients": {
            "кефир",
            "яйца",
            "мука",
            "сахар",
            "масло",
        },
        "instructions": (
            "Смешайте кефир, яйцо, сахар и муку до "
            "густого теста. Выкладывайте ложкой на "
            "разогретую сковороду и обжаривайте с двух сторон."
        ),
    },
    {
        "name": "Яичница с сосисками",
        "ingredients": {
            "яйца",
            "сосиски",
            "масло",
            "соль",
        },
        "instructions": (
            "Нарежьте и слегка обжарьте сосиски. "
            "Добавьте яйца, посолите и готовьте "
            "до желаемой степени прожарки."
        ),
    },
]


PRODUCT_TIPS = {
    "картофель": (
        "Картофель храните в сухом, прохладном и тёмном месте. "
        "Позеленевшие участки и ростки лучше полностью удалить."
    ),
    "яйца": (
        "Яйца лучше хранить в холодильнике в заводской упаковке. "
        "Продукт с повреждённой скорлупой используйте сразу."
    ),
    "сыр": (
        "После вскрытия заверните сыр в пергамент или положите "
        "в закрытый контейнер, чтобы он не высыхал."
    ),
    "курица": (
        "Сырую курицу храните отдельно от готовых продуктов. "
        "После контакта с ней тщательно мойте руки и поверхности."
    ),
    "фарш": (
        "Охлаждённый фарш желательно приготовить как можно скорее. "
        "Не оставляйте его надолго при комнатной температуре."
    ),
    "молоко": (
        "Открытое молоко храните в основной части холодильника, "
        "а не на дверце, где температура меняется чаще."
    ),
    "сметана": (
        "Используйте чистую сухую ложку: так сметана дольше "
        "останется свежей."
    ),
    "творог": (
        "Творог относится к скоропортящимся продуктам. "
        "После вскрытия упаковки не откладывайте его использование."
    ),
    "грибы": (
        "Свежие грибы лучше не мыть заранее. Храните их сухими "
        "в бумажном пакете и мойте непосредственно перед готовкой."
    ),
    "помидоры": (
        "Спелые помидоры лучше использовать быстрее. "
        "Перед употреблением вымойте их под проточной водой."
    ),
    "огурцы": (
        "Огурцы храните сухими в отделении для овощей. "
        "Излишняя влага ускоряет порчу."
    ),
    "зелень": (
        "Зелень можно завернуть в слегка влажное бумажное полотенце "
        "и положить в закрывающийся контейнер."
    ),
    "хлеб": (
        "Если хлеба много, часть можно заморозить порциями. "
        "После размораживания его удобно подсушить."
    ),
    "рис": (
        "Сухой рис держите в герметичной ёмкости. "
        "Готовый рис быстро охлаждайте и храните в холодильнике."
    ),
}


def telegram_request(
    method: str,
    data: dict[str, Any] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    """Выполняет запрос к Telegram Bot API."""
    response = requests.post(
        f"{API_URL}/{method}",
        data=data or {},
        timeout=timeout,
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(
            f"Telegram вернул ошибку: {result}"
        )

    return result


def send_message(
    chat_id: int,
    text: str,
    reply_markup: dict[str, Any] | None = None,
) -> None:
    """Отправляет пользователю сообщение."""
    data: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }

    if reply_markup:
        import json

        data["reply_markup"] = json.dumps(
            reply_markup,
            ensure_ascii=False,
        )

    telegram_request(
        "sendMessage",
        data=data,
        timeout=30,
    )


def fridge_keyboard() -> dict[str, Any]:
    """Создаёт кнопку запуска холодильника."""
    return {
        "keyboard": [
            [
                {
                    "text": "🧊 Что приготовить?"
                }
            ],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
    }


def normalize_ingredient(value: str) -> str:
    """Приводит название продукта к нормальной форме."""
    value = value.lower().strip()

    value = re.sub(
        r"\([^)]*\)",
        "",
        value,
    )

    value = re.sub(
        r"\b\d+(?:[.,]\d+)?\s*"
        r"(?:кг|г|гр|л|мл|шт|штук|упаковк\w*)\b",
        "",
        value,
    )

    value = re.sub(
        r"[^а-яёa-z\- ]",
        "",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

    return INGREDIENT_ALIASES.get(value, value)


def parse_ingredients(text: str) -> set[str]:
    """Извлекает список продуктов из сообщения."""
    text = text.lower()

    text = re.sub(
        r"^(у меня есть|есть|в холодильнике|продукты)\s*:?",
        "",
        text,
    ).strip()

    raw_items = re.split(
        r"[,;\n]+|\s+и\s+",
        text,
    )

    ingredients = {
        normalize_ingredient(item)
        for item in raw_items
        if normalize_ingredient(item)
    }

    return ingredients


def recipe_score(
    recipe: dict[str, Any],
    available: set[str],
) -> tuple[float, set[str], set[str]]:
    """Оценивает, насколько рецепт подходит продуктам пользователя."""
    required = set(recipe["ingredients"])

    useful_required = required - BASIC_PRODUCTS
    available_with_basics = available | BASIC_PRODUCTS

    matched = useful_required & available_with_basics
    missing = useful_required - available_with_basics

    if not useful_required:
        return 0.0, matched, missing

    coverage = len(matched) / len(useful_required)

    # Рецепты с большим количеством совпадений получают преимущество.
    score = (
        coverage * 100
        + len(matched) * 8
        - len(missing) * 13
    )

    return score, matched, missing


def get_best_recipes(
    available: set[str],
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Выбирает самые подходящие блюда."""
    results = []

    for recipe in RECIPES:
        score, matched, missing = recipe_score(
            recipe,
            available,
        )

        # Должен совпасть хотя бы один существенный продукт.
        if not matched:
            continue

        results.append({
            "recipe": recipe,
            "score": score,
            "matched": matched,
            "missing": missing,
        })

    results.sort(
        key=lambda item: (
            item["score"],
            len(item["matched"]),
            -len(item["missing"]),
        ),
        reverse=True,
    )

    return results[:limit]


def build_tips(ingredients: set[str], limit: int = 3) -> list[str]:
    """Подбирает советы для введённых продуктов."""
    tips = []

    for ingredient in sorted(ingredients):
        tip = PRODUCT_TIPS.get(ingredient)

        if tip and tip not in tips:
            tips.append(tip)

        if len(tips) >= limit:
            break

    return tips


def format_recipe_results(ingredients: set[str]) -> str:
    """Формирует ответ с блюдами и советами."""
    results = get_best_recipes(ingredients)

    products_text = ", ".join(
        sorted(ingredients)
    )

    parts = [
        "🧊 В ВАШЕМ ХОЛОДИЛЬНИКЕ",
        "",
        products_text,
        "",
    ]

    if not results:
        parts.extend([
            "🍽 Подходящих блюд пока не найдено.",
            "",
            "Добавьте больше продуктов или укажите их точнее.",
            "",
            "Например:",
            "картофель, яйца, сыр, лук, сметана",
        ])

        return "\n".join(parts)

    parts.extend([
        "🍽 ЧТО МОЖНО ПРИГОТОВИТЬ",
        "",
    ])

    for number, result in enumerate(results, start=1):
        recipe = result["recipe"]
        matched = result["matched"]
        missing = result["missing"]

        matched_text = ", ".join(sorted(matched))

        if missing:
            missing_text = ", ".join(sorted(missing))
        else:
            missing_text = "ничего — всё основное уже есть"

        parts.extend([
            f"{number}. {recipe['name']}",
            f"✅ Уже есть: {matched_text}",
            f"🛒 Докупить: {missing_text}",
            "",
            f"👨‍🍳 {recipe['instructions']}",
            "",
        ])

    tips = build_tips(ingredients)

    if tips:
        parts.extend([
            "💡 ПОЛЕЗНЫЕ СОВЕТЫ",
            "",
        ])

        for tip in tips:
            parts.append(f"• {tip}")

        parts.append("")

    parts.extend([
        "━━━━━━━━━━━━━━",
        "🍽 Больше рецептов:",
        "https://t.me/FoodRadarDaily",
    ])

    return "\n".join(parts).strip()


def start_fridge(chat_id: int) -> None:
    """Переводит пользователя в режим ввода продуктов."""
    WAITING_FOR_INGREDIENTS.add(chat_id)

    send_message(
        chat_id,
        (
            "🧊 ХОЛОДИЛЬНИК\n\n"
            "Напишите продукты, которые у вас есть.\n\n"
            "Можно через запятую или с новой строки.\n\n"
            "Например:\n"
            "картофель, яйца, сыр, лук, сметана"
        ),
        reply_markup=fridge_keyboard(),
    )


def handle_message(message: dict[str, Any]) -> None:
    """Обрабатывает одно входящее сообщение."""
    chat = message.get("chat", {})
    chat_id = chat.get("id")

    if not isinstance(chat_id, int):
        return

    # Работаем только в личной переписке.
    if chat.get("type") != "private":
        return

    text = str(message.get("text", "")).strip()

    if not text:
        return

    lowered = text.lower()

    if lowered in {
        "/start",
        "/help",
    }:
        WAITING_FOR_INGREDIENTS.discard(chat_id)

        send_message(
            chat_id,
            (
                "🍽 FOOD RADAR\n\n"
                "Я помогу подобрать блюда из продуктов, "
                "которые уже есть дома.\n\n"
                "Нажмите кнопку «🧊 Что приготовить?» "
                "или отправьте команду:\n"
                "/холодильник"
            ),
            reply_markup=fridge_keyboard(),
        )
        return

    if (
        lowered in {
            "/холодильник",
            "/fridge",
            "холодильник",
            "🧊 что приготовить?",
        }
        or lowered.startswith("/холодильник ")
        or lowered.startswith("/fridge ")
    ):
        command_parts = text.split(maxsplit=1)

        if len(command_parts) == 2:
            ingredients = parse_ingredients(command_parts[1])

            if ingredients:
                send_message(
                    chat_id,
                    format_recipe_results(ingredients),
                    reply_markup=fridge_keyboard(),
                )
                return

        start_fridge(chat_id)
        return

    if chat_id in WAITING_FOR_INGREDIENTS:
        ingredients = parse_ingredients(text)

        if not ingredients:
            send_message(
                chat_id,
                (
                    "Не удалось распознать продукты.\n\n"
                    "Напишите, например:\n"
                    "курица, картофель, сыр, лук"
                ),
            )
            return

        WAITING_FOR_INGREDIENTS.discard(chat_id)

        send_message(
            chat_id,
            format_recipe_results(ingredients),
            reply_markup=fridge_keyboard(),
        )
        return

    if lowered.startswith(
        (
            "у меня есть ",
            "в холодильнике ",
            "есть ",
        )
    ):
        ingredients = parse_ingredients(text)

        if ingredients:
            send_message(
                chat_id,
                format_recipe_results(ingredients),
                reply_markup=fridge_keyboard(),
            )
            return

    send_message(
        chat_id,
        (
            "Нажмите «🧊 Что приготовить?» и перечислите "
            "продукты, которые есть дома."
        ),
        reply_markup=fridge_keyboard(),
    )


def remove_webhook() -> None:
    """
    Удаляет webhook перед запуском long polling.

    Это нужно, потому что getUpdates не работает,
    пока для бота установлен webhook.
    """
    try:
        telegram_request(
            "deleteWebhook",
            data={
                "drop_pending_updates": False,
            },
            timeout=30,
        )
    except Exception as error:
        print(f"Не удалось проверить webhook: {error}")


def run_bot() -> None:
    """Запускает постоянное получение сообщений."""
    remove_webhook()

    offset = 0

    print("Fridge bot started.")

    while True:
        try:
            result = telegram_request(
                "getUpdates",
                data={
                    "offset": offset,
                    "timeout": 50,
                    "allowed_updates": '["message"]',
                },
                timeout=60,
            )

            updates = result.get("result", [])

            for update in updates:
                update_id = update.get("update_id")

                if isinstance(update_id, int):
                    offset = update_id + 1

                message = update.get("message")

                if isinstance(message, dict):
                    try:
                        handle_message(message)
                    except Exception as error:
                        print(
                            "Ошибка обработки сообщения:",
                            error,
                        )

                        chat_id = message.get(
                            "chat",
                            {},
                        ).get("id")

                        if isinstance(chat_id, int):
                            send_message(
                                chat_id,
                                (
                                    "Произошла временная ошибка. "
                                    "Попробуйте ещё раз."
                                ),
                            )

        except requests.RequestException as error:
            print(f"Ошибка соединения: {error}")
            time.sleep(5)

        except Exception as error:
            print(f"Ошибка цикла бота: {error}")
            time.sleep(5)


if __name__ == "__main__":
    run_bot()
