from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from zoneinfo import ZoneInfo

from zooffer.schemas.account import SubscriptionView
from zooffer.schemas.messaging import ConversationSummaryView
from zooffer.schemas.public import PublicListingCardView, PublicListingView

PURPOSE_LABELS = {
    "sale": "Продажа",
    "mating": "Вязка",
    "breeding_pedigree": "Племенная вязка",
    "adoption": "В добрые руки",
    "rehoming": "Переустройство",
}

SPECIES_LABELS = {
    "dog": "собака",
    "cat": "кошка",
    "bird": "птица",
    "rodent": "грызун",
    "reptile": "рептилия",
    "other": "другое",
}

SEX_LABELS = {"male": "мальчик", "female": "девочка", "unknown": "пол не указан"}

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

MOSCOW = ZoneInfo("Europe/Moscow")


def _when(value: datetime | None) -> str:
    if value is None:
        return "—"
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(MOSCOW).strftime("%d.%m.%Y %H:%M")


def price_label(purpose: str, kopecks: int | None, negotiable: bool = False) -> str:
    if purpose == "adoption" and not kopecks:
        return "В добрые руки"
    if purpose == "rehoming" and not kopecks:
        return "Переустройство"
    if kopecks is None:
        return "Цена по договорённости" if negotiable else "Цена не указана"
    value = f"{kopecks / 100:,.0f}".replace(",", " ")
    suffix = " · торг" if negotiable else ""
    return f"{value} ₽{suffix}"


def public_name(value: str | None) -> str:
    name = (value or "").strip()
    return escape(name) if name else "Владелец"


def listing_card_text(listing: PublicListingCardView, remaining: int, unlimited: bool) -> str:
    city = f" · {escape(listing.city.name)}" if listing.city else ""
    breed = f", {escape(listing.breed)}" if listing.breed else ""
    age = f" · {listing.age_years} г." if listing.age_years is not None else ""
    owner = public_name(listing.owner.display_name)
    quota = (
        "Лимит свайпов: без ограничений" if unlimited else f"Осталось свайпов сегодня: {remaining}"
    )
    return (
        f"<b>{escape(listing.animal_name)}</b>{breed}\n"
        f"{escape(listing.title)}\n"
        f"{PURPOSE_LABELS.get(listing.purpose, listing.purpose)} · "
        f"{price_label(listing.purpose, listing.price_kopecks, listing.negotiable)}\n"
        f"{SPECIES_LABELS.get(listing.species, listing.species)} · "
        f"{SEX_LABELS.get(listing.sex, listing.sex)}{age}{city}\n"
        f"Владелец: {owner}\n\n"
        f"<i>{quota}</i>"
    )


def listing_detail_text(listing: PublicListingView) -> str:
    animal = listing.animal
    city = f" · {escape(listing.city.name)}" if listing.city else ""
    breed = f", {escape(animal.breed)}" if animal.breed else ""
    age = f" · {animal.age_years} г." if animal.age_years is not None else ""
    description = escape((listing.description or "").strip()[:1200])
    lines = [
        f"<b>{escape(listing.title)}</b>",
        f"{escape(animal.name)}{breed}",
        f"{PURPOSE_LABELS.get(listing.purpose, listing.purpose)} · "
        f"{price_label(listing.purpose, listing.price_kopecks, listing.negotiable)}",
        f"{SPECIES_LABELS.get(animal.species, animal.species)} · "
        f"{SEX_LABELS.get(animal.sex, animal.sex)}{age}{city}",
        f"Владелец: {public_name(listing.owner.display_name)}",
    ]
    if description:
        lines.extend(["", description])
    lines.extend(
        [
            "",
            "Контакты и адрес не публикуются. Договоритесь о встрече в чате.",
        ]
    )
    return "\n".join(lines)


def welcome_text(first_name: str) -> str:
    return (
        f"Здравствуйте, <b>{escape(first_name)}</b>!\n\n"
        "Zooffer помогает найти животное и договориться о передаче без публикации "
        "телефонов и адресов. Другие пользователи видят только ваше имя и город.\n\n"
        "Выберите раздел кнопками ниже или откройте Mini App."
    )


def link_confirm_text() -> str:
    return (
        "<b>Привязка Telegram к аккаунту Zooffer</b>\n\n"
        "Подтвердите привязку, чтобы открыть этот аккаунт в боте и Mini App. "
        "Ссылка действует ограниченное время и срабатывает один раз.\n\n"
        "Если вы не запрашивали привязку, нажмите «Отмена»."
    )


def consent_text() -> str:
    return (
        "<b>Добро пожаловать в Zooffer</b>\n\n"
        "Чтобы создать аккаунт, примите Пользовательское соглашение и Политику "
        "конфиденциальности. Мы сохраним версию согласия и канал (Telegram) — это "
        "требование закона о персональных данных.\n\n"
        "Контакты, Telegram username и фото профиля другим пользователям не "
        "показываются."
    )


def name_prompt_text(suggested: str | None) -> str:
    hint = f" Например: <b>{escape(suggested)}</b>." if suggested else ""
    return (
        "Как вас показывать другим пользователям?\n\n"
        "Можно указать только имя — без фамилии, телефона, адреса и ссылок."
        f"{hint}\n\n"
        "Это имя увидят в объявлениях и чатах."
    )


def menu_text(name: str) -> str:
    return (
        f"<b>Меню Zooffer</b>\n\n"
        f"{escape(name)}, выберите действие. Внутри Mini App доступны поиск, "
        "фильтры и полная анкета."
    )


def profile_text(name: str, city: str | None, role: str) -> str:
    rows = [f"<b>{escape(name)}</b>", city or "Город не указан"]
    if role != "user":
        rows.append(f"Роль: {escape(role)}")
    rows.append("Контакты скрыты от других пользователей.")
    return "\n".join(rows)


def help_text() -> str:
    return (
        "<b>Команды Zooffer</b>\n"
        "/start — главное меню\n"
        "/menu — меню\n"
        "/swipe — подбор объявлений\n"
        "/favorites — избранное\n"
        "/chats — переписка\n"
        "/mylistings — мои объявления\n"
        "/addpet — добавить животное и объявление\n"
        "/subscription — подписка и лимит\n"
        "/buy — планы подписки\n"
        "/support — поддержка\n"
        "/settings — уведомления\n"
        "/stop — отключить Telegram-уведомления\n"
        "/news — наш канал\n"
        "/link — привязка аккаунта\n"
        "/language — язык\n\n"
        "Безопасность: не отправляйте предоплату до личной встречи и не переходите "
        "по подозрительным ссылкам."
    )


def settings_text(telegram_on: bool) -> str:
    state = "включены" if telegram_on else "выключены"
    return (
        "<b>Уведомления</b>\n\n"
        f"Telegram-уведомления сейчас {state}. Мы присылаем совпадения, сообщения, "
        "результаты проверки объявлений и статус подписки.\n\n"
        "Тихие часы и отдельные категории настраиваются на сайте в разделе "
        "«Настройки»."
    )


def favorites_text(count: int) -> str:
    if not count:
        return "<b>Избранное</b>\n\nПока пусто. Нажмите «В избранное» на объявлении в подборе."
    return f"<b>Избранное</b>\n\nСохранено объявлений: {count}. Убрать можно кнопкой ниже."


def chats_text(count: int) -> str:
    if not count:
        return (
            "<b>Сообщения</b>\n\n"
            "Диалогов пока нет. Напишите владельцу из объявления — переписка "
            "появится здесь."
        )
    return f"<b>Сообщения</b>\n\nДиалогов: {count}. Выберите, чтобы прочитать и ответить."


def conversation_text(summary: ConversationSummaryView, messages: list[tuple[str, bool]]) -> str:
    name = public_name(summary.counterpart.display_name)
    lines = [f"<b>Диалог с {name}</b>"]
    if summary.listing is not None:
        lines.append(f"Объявление: {escape(summary.listing.title)}")
    if summary.blocked:
        lines.append("Диалог ограничен: одна из сторон заблокировала общение.")
    lines.append("")
    if not messages:
        lines.append("<i>Сообщений пока нет. Напишите первым.</i>")
    for body, mine in reversed(messages):
        prefix = "Вы" if mine else name
        line = f"<b>{prefix}:</b> {escape(body[:500])}"
        if sum(len(item) for item in lines) + len(line) > 3400:
            lines.append("<i>…</i>")
            break
        lines.append(line)
    return "\n".join(lines)


def no_new_listings_text() -> str:
    return (
        "<b>Подбор</b>\n\n"
        "Новых объявлений по вашим параметрам пока нет. Загляните позже или "
        "измените фильтры в Mini App."
    )


def quota_exceeded_text(reset_at: str | None = None) -> str:
    suffix = f" Лимит обновится {reset_at}." if reset_at else ""
    return (
        "Дневной лимит показов закончился."
        f"{suffix}\n\n"
        "Оформить подписку можно в разделе «Подписка»."
    )


def listing_created_text(title: str) -> str:
    return (
        f"<b>{escape(title)}</b>\n\n"
        "Черновик создан. Добавьте хотя бы одну фотографию, затем подтвердите "
        "публикацию."
    )


def publish_checklist_text(title: str) -> str:
    return (
        f"<b>Публикация: {escape(title)}</b>\n\n"
        "Подтвердите все пункты одним нажатием:\n"
        "• животное достигло допустимого возраста;\n"
        "• условия содержания и передачи безопасны для животного;\n"
        "• фотографии принадлежат вам и не нарушают чужие права;\n"
        "• в объявлении нет запрещённых товаров и услуг;\n"
        "• данные и цена указаны верно.\n\n"
        "После публикации объявление проходит автоматическую проверку."
    )


def listing_published_text(title: str, status: str, reason: str | None = None) -> str:
    if status == "published":
        return (
            f"<b>{escape(title)}</b>\n\n"
            "Объявление опубликовано. Ссылка доступна в Mini App и на сайте."
        )
    return (
        f"<b>{escape(title)}</b>\n\n"
        "Объявление отправлено на проверку. Мы пришлём уведомление о результате."
        + (f"\n\nКомментарий: {escape(reason)}" if reason else "")
    )


def my_listings_text(count: int) -> str:
    if not count:
        return "<b>Мои объявления</b>\n\nОбъявлений пока нет. Добавьте животное командой /addpet."
    return (
        f"<b>Мои объявления</b>\n\nВсего: {count}. Выберите объявление, чтобы "
        "посмотреть статус или изменить его."
    )


def subscription_text(subscription: SubscriptionView) -> str:
    if subscription.status == "none" or not subscription.plan_name:
        plan_line = "Активной подписки нет."
        period = ""
    else:
        plan_line = f"План: <b>{escape(subscription.plan_name)}</b> ({subscription.status})."
        period = (
            f"\nДействует до: {_when(subscription.current_period_end)}"
            if subscription.current_period_end
            else ""
        )
    if subscription.quota_unlimited:
        quota = "Свайпы: без ограничений."
    else:
        quota = f"Свайпов в день: {subscription.quota_limit}."
    entitlements = (
        "Возможности: " + ", ".join(escape(item) for item in subscription.entitlements)
        if subscription.entitlements
        else ""
    )
    return "\n\n".join(
        part for part in ["<b>Подписка</b>", plan_line + period, quota, entitlements] if part
    )


def plans_text(has_plans: bool, payments_available: bool) -> str:
    if not has_plans:
        return "<b>Планы</b>\n\nПланы пока не настроены."
    if not payments_available:
        return (
            "<b>Планы</b>\n\n"
            "Платные планы появятся после подключения платёжного провайдера. "
            "Сейчас доступен бесплатный дневной лимит свайпов.\n\n"
            "Если нужен особый доступ, напишите в поддержку."
        )
    return (
        "<b>Планы</b>\n\n"
        "Выберите план. Оплата откроется на сайте или в Mini App после "
        "подтверждения провайдера."
    )


def plan_payment_unavailable_text() -> str:
    return (
        "Онлайн-оплата пока не подключена в этой среде. Мы не берём деньги без "
        "рабочего платёжного провайдера и чека.\n\n"
        "Напишите в поддержку — поможем с доступом."
    )


def support_intro_text() -> str:
    return (
        "<b>Поддержка Zooffer</b>\n\n"
        "Опишите проблему в двух шагах: тема и сообщение. Не отправляйте пароли, "
        "коды из SMS и полные данные карты.\n\n"
        "Ответ придёт в этот чат и в раздел поддержки на сайте."
    )


def support_subject_prompt() -> str:
    return "Шаг 1 из 2. Укажите тему обращения (3–160 символов)."


def support_message_prompt() -> str:
    return "Шаг 2 из 2. Опишите ситуацию (10–5000 символов). Можно приложить ссылку на объявление."


def support_created_text(public_id: str) -> str:
    return (
        "<b>Обращение создано</b>\n\n"
        f"Номер: <code>{escape(public_id)}</code>\n"
        "Мы ответим в этом чате. Спасибо, что помогаете сделать Zooffer безопаснее."
    )


def support_cancelled_text() -> str:
    return "Обращение отменено. Если понадобится помощь, вызовите /support."


def news_text(channel_url: str) -> str:
    if not channel_url:
        return "Канал Zooffer пока не настроен в этой среде."
    return "<b>Новости Zooffer</b>\n\nОбновления продукта, правила и полезные материалы."


def language_text() -> str:
    return "<b>Язык</b>\n\nСейчас интерфейс доступен на русском языке. Другие языки появятся позже."


def link_text(bot_username: str) -> str:
    if not bot_username:
        return (
            "<b>Привязка аккаунта</b>\n\n"
            "Привязка выполняется со стороны сайта: откройте «Настройки» → "
            "«Привязать Telegram» и перейдите по ссылке из бота."
        )
    return (
        "<b>Привязка аккаунта</b>\n\n"
        "Чтобы связать сайт и Telegram, откройте на сайте «Настройки» → "
        "«Привязать Telegram» и перейдите по ссылке.\n\n"
        f"Бот: @{escape(bot_username)}"
    )


def settings_disabled_note() -> str:
    return "Telegram-уведомления выключены. Включить можно в /settings."


def match_text() -> str:
    return (
        "<b>Взаимная симпатия!</b>\n\n"
        "Вам ответили взаимностью. Чат уже создан — договоритесь о деталях "
        "без публикации контактов."
    )


def generic_error_text() -> str:
    return (
        "Что-то пошло не так. Попробуйте ещё раз или откройте меню командой /menu.\n\n"
        "Если ошибка повторяется, напишите в /support."
    )


def wizard_species_text() -> str:
    return "<b>Новое объявление</b>\n\nШаг 1 из 9. Кто это?"


def wizard_sex_text(name: str) -> str:
    return f"Шаг 2 из 9. Укажите пол: <b>{escape(name)}</b>."


def wizard_name_text() -> str:
    return "Шаг 3 из 9. Как зовут животное? Укажите имя (до 80 символов)."


def wizard_birth_text() -> str:
    return (
        "Шаг 4 из 9. Дата рождения: <code>ГГГГ-ММ-ДД</code>, <code>ДД.ММ.ГГГГ</code> "
        "или просто год. Можно пропустить."
    )


def wizard_city_text() -> str:
    return (
        "Шаг 5 из 9. Укажите город (например, Москва). Город видят другие "
        "пользователи; точный адрес не публикуется. Можно пропустить."
    )


def wizard_purpose_text() -> str:
    return "Шаг 6 из 9. Выберите цель объявления."


def wizard_title_text() -> str:
    return "Шаг 7 из 9. Заголовок объявления (5–140 символов)."


def wizard_description_text() -> str:
    return (
        "Шаг 8 из 9. Опишите животное, характер и условия передачи "
        "(до 5000 символов). Не указывайте телефон, адрес и ссылки. Можно пропустить."
    )


def wizard_price_text() -> str:
    return (
        "Шаг 9 из 9. Укажите цену в рублях или выберите «По договорённости».\n\n"
        "Не указывайте цену, если отдаёте животное бесплатно — выберите "
        "«В добрые руки»."
    )


def wizard_photo_text(count: int) -> str:
    return (
        f"<b>Фотографии: {count}</b>\n\n"
        "Отправьте фото животного. Поддерживаются JPG, PNG и WebP, до 8 МБ. "
        "Первое фото станет главным. Нужна хотя бы одна фотография."
    )


def wizard_cancelled_text() -> str:
    return "Создание объявления отменено. Черновик, если он уже создан, сохранится в /mylistings."


def wizard_invalid_birth_text() -> str:
    return "Не понял дату. Укажите ГГГГ-ММ-ДД, ДД.ММ.ГГГГ, год или пропустите."


def wizard_city_not_found_text(value: str) -> str:
    return f"Город «{escape(value[:60])}» не найден. Попробуйте другое название или пропустите шаг."


def wizard_invalid_price_text() -> str:
    return "Укажите цену целым числом рублей (до 1 000 000) или выберите «По договорённости»."


def owner_listing_text(listing, animal, has_photos: bool) -> str:
    status = STATUS_LABELS.get(listing.status, listing.status)
    lines = [
        f"<b>{escape(listing.title)}</b>",
        f"Животное: {escape(animal.name)}",
        f"Статус: <b>{status}</b>",
        f"{PURPOSE_LABELS.get(listing.purpose, listing.purpose)} · "
        f"{price_label(listing.purpose, listing.price_kopecks, listing.negotiable)}",
        f"Фотографий: {'есть' if has_photos else 'нет'}",
    ]
    if listing.moderation_reason:
        lines.append(f"Комментарий проверки: {escape(listing.moderation_reason)}")
    if listing.expires_at:
        lines.append(f"Действует до: {_when(listing.expires_at)}")
    return "\n".join(lines)


def photo_required_text() -> str:
    return "Сначала добавьте хотя бы одну фотографию."


def photo_added_text(count: int) -> str:
    return f"Фото добавлено. Всего фотографий: {count}."


def invalid_name_text() -> str:
    return (
        "Имя должно содержать только буквы, пробел, дефис или апостроф "
        "(до 40 символов) и не содержать контактов или ссылок."
    )
