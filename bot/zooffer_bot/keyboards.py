from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from .callbacks import pack

PURPOSE_OPTIONS = (
    ("adoption", "В добрые руки"),
    ("rehoming", "Переустройство"),
    ("sale", "Продажа"),
    ("mating", "Вязка"),
    ("breeding_pedigree", "Племенная вязка"),
)

SPECIES_OPTIONS = (
    ("dog", "Собака"),
    ("cat", "Кошка"),
    ("bird", "Птица"),
    ("rodent", "Грызун"),
    ("reptile", "Рептилия"),
    ("other", "Другое"),
)

STATUS_LABELS = {
    "draft": "черновик",
    "pending_moderation": "на проверке",
    "published": "опубликовано",
    "paused": "приостановлено",
    "expired": "истекло",
    "sold": "передано",
    "archived": "в архиве",
    "rejected": "отклонено",
}


def _web_app(url: str) -> WebAppInfo | None:
    return WebAppInfo(url=url) if url.startswith("https://") else None


def main_reply_keyboard(mini_app_url: str) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text="Меню")]]
    web_app = _web_app(mini_app_url)
    if web_app is not None:
        rows.insert(0, [KeyboardButton(text="Открыть Zooffer", web_app=web_app)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def main_menu(mini_app_url: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="Подбор", callback_data=pack("menu", "swipe")),
            InlineKeyboardButton(text="Избранное", callback_data=pack("menu", "favorites")),
        ],
        [
            InlineKeyboardButton(text="Сообщения", callback_data=pack("menu", "chats")),
            InlineKeyboardButton(text="Мои объявления", callback_data=pack("menu", "listings")),
        ],
        [
            InlineKeyboardButton(text="Профиль", callback_data=pack("menu", "profile")),
            InlineKeyboardButton(text="Помощь", callback_data=pack("menu", "help")),
        ],
    ]
    web_app = _web_app(mini_app_url)
    if web_app is not None:
        rows.append([InlineKeyboardButton(text="Открыть Zooffer", web_app=web_app)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def consent_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Принимаю условия", callback_data=pack("onb", "accept")
                )
            ],
            [InlineKeyboardButton(text="Отмена", callback_data=pack("onb", "cancel"))],
        ]
    )


def link_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Подтвердить привязку", callback_data=pack("link", "confirm")
                )
            ],
            [InlineKeyboardButton(text="Отмена", callback_data=pack("link", "cancel"))],
        ]
    )


def name_keyboard(suggested: str | None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if suggested:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"Использовать «{suggested[:32]}»",
                    callback_data=pack("onb", "suggested"),
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="Отмена", callback_data=pack("onb", "cancel"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data=pack("menu", "home"))]]
    )


def swipe_keyboard(listing_public_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Пропустить", callback_data=pack("sw", "skip", listing_public_id)
                ),
                InlineKeyboardButton(
                    text="Нравится", callback_data=pack("sw", "like", listing_public_id)
                ),
            ],
            [
                InlineKeyboardButton(
                    text="В избранное", callback_data=pack("sw", "fav", listing_public_id)
                ),
            ],
        ]
    )


def public_listing_keyboard(listing_public_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Написать владельцу",
                    callback_data=pack("ch", "inquire", listing_public_id),
                )
            ],
            [
                InlineKeyboardButton(
                    text="В избранное",
                    callback_data=pack("sw", "fav", listing_public_id),
                )
            ],
            [InlineKeyboardButton(text="В меню", callback_data=pack("menu", "home"))],
        ]
    )


def next_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Дальше", callback_data=pack("menu", "swipe")),
                InlineKeyboardButton(text="В меню", callback_data=pack("menu", "home")),
            ]
        ]
    )


def match_keyboard(conversation_public_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть чат",
                    callback_data=pack("ch", "open", conversation_public_id),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Продолжить подбор", callback_data=pack("menu", "swipe")
                )
            ],
        ]
    )


def favorites_keyboard(items: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"Убрать «{label[:24]}»", callback_data=pack("fav", "rm", public_id)
            )
        ]
        for public_id, label in items[:10]
    ]
    rows.append([InlineKeyboardButton(text="В меню", callback_data=pack("menu", "home"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def chats_keyboard(items: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=label[:48], callback_data=pack("ch", "open", public_id)
            )
        ]
        for public_id, label in items[:10]
    ]
    rows.append([InlineKeyboardButton(text="В меню", callback_data=pack("menu", "home"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def chat_keyboard(conversation_public_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Ответить",
                    callback_data=pack("ch", "reply", conversation_public_id),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Все диалоги", callback_data=pack("menu", "chats")
                )
            ],
            [InlineKeyboardButton(text="В меню", callback_data=pack("menu", "home"))],
        ]
    )


def listings_keyboard(items: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=label[:48], callback_data=pack("ml", "open", public_id)
            )
        ]
        for public_id, label in items[:10]
    ]
    rows.append(
        [
            InlineKeyboardButton(text="Добавить", callback_data=pack("menu", "addpet")),
            InlineKeyboardButton(text="В меню", callback_data=pack("menu", "home")),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def listing_actions_keyboard(
    listing_public_id: str, status: str, *, has_photos: bool
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if status in {"draft", "rejected", "paused", "expired"}:
        if has_photos:
            rows.append(
                [
                    InlineKeyboardButton(
                        text="Опубликовать",
                        callback_data=pack("ml", "pub", listing_public_id),
                    )
                ]
            )
        else:
            rows.append(
                [
                    InlineKeyboardButton(
                        text="Добавить фото",
                        callback_data=pack("ml", "photo", listing_public_id),
                    )
                ]
            )
    if status == "published":
        rows.append(
            [
                InlineKeyboardButton(
                    text="Приостановить",
                    callback_data=pack("ml", "pause", listing_public_id),
                ),
                InlineKeyboardButton(
                    text="Передано",
                    callback_data=pack("ml", "sold", listing_public_id),
                ),
            ]
        )
    if status not in {"archived"}:
        rows.append(
            [
                InlineKeyboardButton(
                    text="В архив",
                    callback_data=pack("ml", "archive", listing_public_id),
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="Мои объявления", callback_data=pack("menu", "listings")
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def publish_confirm_keyboard(listing_public_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Публикую",
                    callback_data=pack("ml", "pubok", listing_public_id),
                )
            ],
            [InlineKeyboardButton(text="Отмена", callback_data=pack("menu", "listings"))],
        ]
    )


def profile_keyboard(mini_app_url: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="Настройки", callback_data=pack("menu", "settings")),
            InlineKeyboardButton(
                text="Подписка", callback_data=pack("menu", "subscription")
            ),
        ],
        [InlineKeyboardButton(text="Поддержка", callback_data=pack("menu", "support"))],
        [InlineKeyboardButton(text="В меню", callback_data=pack("menu", "home"))],
    ]
    web_app = _web_app(f"{mini_app_url}/profile")
    if web_app is not None:
        rows.insert(0, [InlineKeyboardButton(text="Открыть профиль", web_app=web_app)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def settings_keyboard(telegram_on: bool) -> InlineKeyboardMarkup:
    toggle = "Выключить уведомления" if telegram_on else "Включить уведомления"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=toggle, callback_data=pack("set", "notify"))],
            [InlineKeyboardButton(text="В меню", callback_data=pack("menu", "home"))],
        ]
    )


def subscription_keyboard(has_plans: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if has_plans:
        rows.append(
            [InlineKeyboardButton(text="Выбрать план", callback_data=pack("menu", "buy"))]
        )
    rows.append([InlineKeyboardButton(text="Поддержка", callback_data=pack("menu", "support"))])
    rows.append([InlineKeyboardButton(text="В меню", callback_data=pack("menu", "home"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def plans_keyboard(plans: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=label[:48], callback_data=pack("buy", "plan", code[:24])
            )
        ]
        for code, label in plans[:8]
    ]
    rows.append([InlineKeyboardButton(text="Назад", callback_data=pack("menu", "subscription"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def support_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data=pack("sup", "cancel"))]
        ]
    )


def purpose_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=label, callback_data=pack("pet", "purpose", value))
                for value, label in PURPOSE_OPTIONS[:2]
            ],
            [
                InlineKeyboardButton(text=label, callback_data=pack("pet", "purpose", value))
                for value, label in PURPOSE_OPTIONS[2:4]
            ],
            [
                InlineKeyboardButton(
                    text=PURPOSE_OPTIONS[4][1],
                    callback_data=pack("pet", "purpose", PURPOSE_OPTIONS[4][0]),
                )
            ],
            [InlineKeyboardButton(text="Отмена", callback_data=pack("pet", "cancel"))],
        ]
    )


def species_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text=label, callback_data=pack("pet", "species", value))
            for value, label in SPECIES_OPTIONS[index : index + 3]
        ]
        for index in range(0, len(SPECIES_OPTIONS), 3)
    ]
    rows.append([InlineKeyboardButton(text="Отмена", callback_data=pack("pet", "cancel"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def sex_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Мальчик", callback_data=pack("pet", "sex", "male")),
                InlineKeyboardButton(
                    text="Девочка", callback_data=pack("pet", "sex", "female")
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Неизвестно", callback_data=pack("pet", "sex", "unknown")
                )
            ],
            [InlineKeyboardButton(text="Отмена", callback_data=pack("pet", "cancel"))],
        ]
    )


def skip_keyboard(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Пропустить", callback_data=pack("pet", action))],
            [InlineKeyboardButton(text="Отмена", callback_data=pack("pet", "cancel"))],
        ]
    )


def price_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="По договорённости", callback_data=pack("pet", "negotiable")
                )
            ],
            [InlineKeyboardButton(text="Отмена", callback_data=pack("pet", "cancel"))],
        ]
    )


def photo_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Добавить ещё фото", callback_data=pack("pet", "morephoto")
                )
            ],
            [
                InlineKeyboardButton(
                    text="К публикации", callback_data=pack("pet", "readypublish")
                )
            ],
            [InlineKeyboardButton(text="Отмена", callback_data=pack("pet", "cancel"))],
        ]
    )


def news_keyboard(channel_url: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if channel_url.startswith("https://"):
        rows.append(
            [InlineKeyboardButton(text="Открыть канал", url=channel_url)]
        )
    rows.append([InlineKeyboardButton(text="В меню", callback_data=pack("menu", "home"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)
