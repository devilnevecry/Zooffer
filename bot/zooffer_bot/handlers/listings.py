from __future__ import annotations

import re
from datetime import date
from io import BytesIO
from uuid import UUID

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from zooffer.core.enums import AnimalSize, ListingPurpose, Sex, Species
from zooffer.core.errors import AppError, ValidationAppError
from zooffer.core.utils import utcnow
from zooffer.db.models import User
from zooffer.schemas.listing import AnimalCreateRequest, ListingCreateRequest
from zooffer.services import listing_service

from .. import services, texts
from ..callbacks import prefix, unpack
from ..config import BotConfig
from ..keyboards import (
    listing_actions_keyboard,
    listings_keyboard,
    photo_keyboard,
    price_keyboard,
    publish_confirm_keyboard,
    purpose_keyboard,
    sex_keyboard,
    skip_keyboard,
    species_keyboard,
)
from ..states import ListingWizard
from .common import ensure_onboarded, safe_callback_answer

router = Router(name="listings")

MAX_DESCRIPTION = 5000
MAX_PRICE_RUBLES = 1_000_000


def _parse_birth(value: str) -> date | None:
    cleaned = value.strip().lower()
    if cleaned in {"пропустить", "skip", "-"}:
        return None
    candidate: date | None = None
    if re.fullmatch(r"\d{4}", cleaned):
        candidate = date(int(cleaned), 1, 1)
    else:
        for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
            try:
                from datetime import datetime

                candidate = datetime.strptime(cleaned, fmt).date()
                break
            except ValueError:
                continue
    if candidate is None:
        raise ValidationAppError(texts.wizard_invalid_birth_text(), code="invalid_birth_date")
    if candidate > date.today():
        raise ValidationAppError("Дата рождения не может быть в будущем.", code="future_birth_date")
    if candidate.year < 1980:
        raise ValidationAppError("Проверьте год рождения.", code="invalid_birth_date")
    return candidate


def _parse_price(value: str) -> tuple[int, bool]:
    cleaned = value.strip()
    if cleaned.lower() in {"по договорённости", "договор", "торг", "negotiable", "-"}:
        return 0, True
    digits = re.sub(r"[^\d]", "", cleaned)
    if not digits:
        raise ValidationAppError(texts.wizard_invalid_price_text(), code="invalid_price")
    rubles = int(digits)
    if rubles <= 0 or rubles > MAX_PRICE_RUBLES:
        raise ValidationAppError(texts.wizard_invalid_price_text(), code="invalid_price")
    return rubles * 100, False


async def begin_wizard(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(ListingWizard.species)
    await message.answer(texts.wizard_species_text(), reply_markup=species_keyboard())


async def show_listings(message: Message, db: AsyncSession, user: User) -> None:
    rows = await services.owned_listings(db, user)
    labels = [
        (
            str(listing.public_id),
            f"{animal.name} · "
            f"{texts.STATUS_LABELS.get(listing.status, listing.status)}",
        )
        for listing, animal, _has_photo in rows
    ]
    await message.answer(
        texts.my_listings_text(len(rows)),
        reply_markup=listings_keyboard(labels),
    )


async def _send_owner_listing(
    message: Message,
    db: AsyncSession,
    user: User,
    listing_public_id: UUID,
) -> None:
    listing, animal, has_photo = await services.owned_listing(db, user, listing_public_id)
    await message.answer(
        texts.owner_listing_text(listing, animal, has_photo),
        reply_markup=listing_actions_keyboard(
            str(listing.public_id), listing.status, has_photos=has_photo
        ),
    )


@router.message(Command("mylistings"))
async def cmd_my_listings(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
    config: BotConfig,
) -> None:
    if user is None:
        if await ensure_onboarded(message, user, state, config):
            return
        return
    await state.clear()
    await show_listings(message, db, user)


@router.message(Command("addpet"))
async def cmd_addpet(
    message: Message,
    state: FSMContext,
    user: User | None,
    config: BotConfig,
) -> None:
    if user is None:
        if await ensure_onboarded(message, user, state, config):
            return
        return
    await begin_wizard(message, state)


@router.callback_query(
    F.data.startswith(prefix("pet:species:")), StateFilter(ListingWizard.species)
)
async def pet_species(
    callback: CallbackQuery, state: FSMContext, user: User | None
) -> None:
    if user is None:
        await safe_callback_answer(callback, "Сначала отправьте /start.")
        return
    parts = unpack(callback.data, 3)
    if parts is None or parts[1] != "species":
        await safe_callback_answer(callback, "Кнопка устарела.")
        return
    await state.update_data(species=parts[2], animal_name=None)
    await state.set_state(ListingWizard.sex)
    await safe_callback_answer(callback)
    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            texts.wizard_sex_text(texts.SPECIES_LABELS.get(parts[2], "питомец")),
            reply_markup=sex_keyboard(),
        )


@router.callback_query(F.data.startswith(prefix("pet:sex:")), StateFilter(ListingWizard.sex))
async def pet_sex(
    callback: CallbackQuery, state: FSMContext, user: User | None
) -> None:
    if user is None:
        await safe_callback_answer(callback, "Сначала отправьте /start.")
        return
    parts = unpack(callback.data, 3)
    if parts is None or parts[1] != "sex":
        await safe_callback_answer(callback, "Кнопка устарела.")
        return
    await state.update_data(sex=parts[2])
    await state.set_state(ListingWizard.name)
    await safe_callback_answer(callback)
    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(texts.wizard_name_text())


@router.message(ListingWizard.name, F.text)
async def pet_name(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if not value or len(value) > 80:
        await message.answer("Укажите имя животного (до 80 символов).")
        return
    await state.update_data(animal_name=value)
    await state.set_state(ListingWizard.birth)
    await message.answer(
        texts.wizard_birth_text(), reply_markup=skip_keyboard("skipbirth")
    )


@router.callback_query(F.data.startswith(prefix("pet:skipbirth")), StateFilter(ListingWizard.birth))
async def pet_skip_birth(
    callback: CallbackQuery, state: FSMContext, user: User | None
) -> None:
    if user is None:
        await safe_callback_answer(callback, "Сначала отправьте /start.")
        return
    await state.update_data(birth_date=None)
    await state.set_state(ListingWizard.city)
    await safe_callback_answer(callback)
    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            texts.wizard_city_text(), reply_markup=skip_keyboard("skipcity")
        )


@router.message(ListingWizard.birth, F.text)
async def pet_birth(message: Message, state: FSMContext) -> None:
    try:
        birth = _parse_birth(message.text or "")
    except AppError as exc:
        await message.answer(exc.message, reply_markup=skip_keyboard("skipbirth"))
        return
    await state.update_data(birth_date=birth.isoformat() if birth else None)
    await state.set_state(ListingWizard.city)
    await message.answer(
        texts.wizard_city_text(), reply_markup=skip_keyboard("skipcity")
    )


@router.callback_query(F.data.startswith(prefix("pet:skipcity")), StateFilter(ListingWizard.city))
async def pet_skip_city(
    callback: CallbackQuery, state: FSMContext, user: User | None
) -> None:
    if user is None:
        await safe_callback_answer(callback, "Сначала отправьте /start.")
        return
    await state.update_data(city_id=None, city_name=None)
    await state.set_state(ListingWizard.purpose)
    await safe_callback_answer(callback)
    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            texts.wizard_purpose_text(), reply_markup=purpose_keyboard()
        )


@router.message(ListingWizard.city, F.text)
async def pet_city(
    message: Message, state: FSMContext, db: AsyncSession
) -> None:
    value = (message.text or "").strip()
    if value.lower() in {"пропустить", "skip", "-"}:
        await state.update_data(city_id=None, city_name=None)
        await state.set_state(ListingWizard.purpose)
        await message.answer(
            texts.wizard_purpose_text(), reply_markup=purpose_keyboard()
        )
        return
    city = await services.find_city(db, value)
    if city is None:
        await message.answer(
            texts.wizard_city_not_found_text(value),
            reply_markup=skip_keyboard("skipcity"),
        )
        return
    await state.update_data(city_id=city.id, city_name=city.name)
    await state.set_state(ListingWizard.purpose)
    await message.answer(
        texts.wizard_purpose_text(), reply_markup=purpose_keyboard()
    )


@router.callback_query(
    F.data.startswith(prefix("pet:purpose:")), StateFilter(ListingWizard.purpose)
)
async def pet_purpose(
    callback: CallbackQuery, state: FSMContext, user: User | None
) -> None:
    if user is None:
        await safe_callback_answer(callback, "Сначала отправьте /start.")
        return
    parts = unpack(callback.data, 3)
    if parts is None or parts[1] != "purpose":
        await safe_callback_answer(callback, "Кнопка устарела.")
        return
    try:
        purpose = ListingPurpose(parts[2])
    except ValueError:
        await safe_callback_answer(callback, "Неизвестная цель.")
        return
    await state.update_data(purpose=purpose.value)
    await state.set_state(ListingWizard.title)
    await safe_callback_answer(callback)
    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(texts.wizard_title_text())


@router.message(ListingWizard.title, F.text)
async def pet_title(message: Message, state: FSMContext) -> None:
    value = " ".join((message.text or "").split())
    if len(value) < 5 or len(value) > 140:
        await message.answer("Заголовок должен быть от 5 до 140 символов.")
        return
    await state.update_data(title=value)
    await state.set_state(ListingWizard.description)
    await message.answer(
        texts.wizard_description_text(), reply_markup=skip_keyboard("skipdesc")
    )


@router.callback_query(
    F.data.startswith(prefix("pet:skipdesc")), StateFilter(ListingWizard.description)
)
async def pet_skip_description(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
    bot: Bot,
) -> None:
    if user is None:
        await safe_callback_answer(callback, "Сначала отправьте /start.")
        return
    await state.update_data(description="")
    await safe_callback_answer(callback)
    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        await _after_description(callback.message, state, db, user, bot)


@router.message(ListingWizard.description, F.text)
async def pet_description(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
    bot: Bot,
) -> None:
    value = (message.text or "").strip()
    if len(value) > MAX_DESCRIPTION:
        await message.answer("Описание слишком длинное (до 5000 символов).")
        return
    await state.update_data(description=value)
    await _after_description(message, state, db, user, bot)


async def _after_description(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
    bot: Bot,
) -> None:
    if user is None:
        await state.clear()
        return
    data = await state.get_data()
    if data.get("purpose") == ListingPurpose.SALE.value:
        await state.set_state(ListingWizard.price)
        await message.answer(
            texts.wizard_price_text(), reply_markup=price_keyboard()
        )
        return
    await _create_draft(message, state, db, user, bot)


@router.callback_query(
    F.data.startswith(prefix("pet:negotiable")), StateFilter(ListingWizard.price)
)
async def pet_negotiable(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
    bot: Bot,
) -> None:
    if user is None:
        await safe_callback_answer(callback, "Сначала отправьте /start.")
        return
    await state.update_data(price_kopecks=None, negotiable=True)
    await safe_callback_answer(callback)
    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        await _create_draft(callback.message, state, db, user, bot)


@router.message(ListingWizard.price, F.text)
async def pet_price(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
    bot: Bot,
) -> None:
    try:
        price, negotiable = _parse_price(message.text or "")
    except AppError as exc:
        await message.answer(exc.message, reply_markup=price_keyboard())
        return
    await state.update_data(price_kopecks=price or None, negotiable=negotiable)
    await _create_draft(message, state, db, user, bot)


async def _create_draft(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    data = await state.get_data()
    animal = None
    try:
        animal = await listing_service.create_animal(
            db,
            user,
            AnimalCreateRequest(
                name=data["animal_name"],
                species=Species(data["species"]),
                sex=Sex(data.get("sex", "unknown")),
                birth_date=(
                    date.fromisoformat(data["birth_date"])
                    if data.get("birth_date")
                    else None
                ),
                size=AnimalSize.UNKNOWN,
            ),
        )
        listing = await listing_service.create_listing(
            db,
            user,
            ListingCreateRequest(
                animal_id=animal.public_id,
                purpose=ListingPurpose(data["purpose"]),
                title=data["title"],
                description=data.get("description", ""),
                price_kopecks=data.get("price_kopecks"),
                negotiable=bool(data.get("negotiable")),
                city_id=data.get("city_id"),
            ),
        )
    except AppError as exc:
        if animal is not None:
            animal.archived_at = utcnow()
            await db.commit()
        await state.clear()
        await message.answer(exc.message)
        return
    await state.update_data(
        animal_public_id=str(animal.public_id),
        listing_public_id=str(listing.public_id),
        listing_title=listing.title,
    )
    await state.set_state(ListingWizard.photos)
    await message.answer(
        texts.listing_created_text(listing.title),
        reply_markup=photo_keyboard(),
    )
    await message.answer(
        texts.wizard_photo_text(0),
        reply_markup=photo_keyboard(),
    )


async def _photo_count(
    db: AsyncSession, user: User, listing_public_id: UUID
) -> tuple[int, bool]:
    from sqlalchemy import func, select
    from zooffer.db.models import AnimalPhoto

    listing, animal, has_photo = await services.owned_listing(db, user, listing_public_id)
    del listing
    count = await db.scalar(
        select(func.count())
        .select_from(AnimalPhoto)
        .where(AnimalPhoto.animal_id == animal.id)
    )
    return int(count or 0), has_photo


@router.message(ListingWizard.photos, F.photo)
async def pet_photo(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
    bot: Bot,
) -> None:
    if user is None:
        await state.clear()
        return
    data = await state.get_data()
    raw_animal = data.get("animal_public_id")
    raw_listing = data.get("listing_public_id")
    animal_public_id = await services.parse_listing_public_id(raw_animal) if raw_animal else None
    listing_public_id = await services.parse_listing_public_id(raw_listing) if raw_listing else None
    if animal_public_id is None or listing_public_id is None:
        await state.clear()
        await message.answer("Черновик не найден. Начните заново: /addpet")
        return
    if not message.photo:
        await message.answer(texts.wizard_photo_text(0))
        return
    buffer = BytesIO()
    try:
        await message.bot.download(message.photo[-1], destination=buffer)
        content = buffer.getvalue()
        await services.add_photo(db, user, animal_public_id, content)
    except AppError as exc:
        await message.answer(exc.message, reply_markup=photo_keyboard())
        return
    except TelegramBadRequest:
        await message.answer(
            "Не удалось скачать фото. Отправьте файл ещё раз.", reply_markup=photo_keyboard()
        )
        return
    count, _ = await _photo_count(db, user, listing_public_id)
    await message.answer(
        texts.photo_added_text(count), reply_markup=photo_keyboard()
    )


@router.message(ListingWizard.photos, F.text)
async def pet_photo_text(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
    bot: Bot,
) -> None:
    if user is None:
        await state.clear()
        return
    data = await state.get_data()
    raw_listing = data.get("listing_public_id")
    listing_public_id = await services.parse_listing_public_id(raw_listing) if raw_listing else None
    if listing_public_id is None:
        await state.clear()
        await message.answer("Черновик не найден. Начните заново: /addpet")
        return
    count, has_photo = await _photo_count(db, user, listing_public_id)
    if (message.text or "").strip().lower() in {"готово", "к публикации", "опубликовать"}:
        if not has_photo:
            await message.answer(texts.photo_required_text(), reply_markup=photo_keyboard())
            return
        await _send_publish_checklist(message, state, listing_public_id, data)
        return
    await message.answer(texts.wizard_photo_text(count), reply_markup=photo_keyboard())


async def _send_publish_checklist(
    message: Message,
    state: FSMContext,
    listing_public_id: UUID,
    data: dict,
) -> None:
    await state.set_state(ListingWizard.confirm)
    title = str(data.get("listing_title") or "объявление")
    await message.answer(
        texts.publish_checklist_text(title),
        reply_markup=publish_confirm_keyboard(str(listing_public_id)),
    )


@router.callback_query(
    F.data.startswith(prefix("pet:morephoto")),
    StateFilter(ListingWizard.photos, ListingWizard.confirm),
)
async def pet_more_photo(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, user: User | None
) -> None:
    if user is None:
        await safe_callback_answer(callback, "Сначала отправьте /start.")
        return
    await state.set_state(ListingWizard.photos)
    await safe_callback_answer(callback)
    if callback.message is not None:
        data = await state.get_data()
        raw_listing = data.get("listing_public_id")
        listing_public_id = (
            await services.parse_listing_public_id(raw_listing) if raw_listing else None
        )
        count = 0
        if listing_public_id is not None:
            count, _ = await _photo_count(db, user, listing_public_id)
        await callback.message.answer(
            texts.wizard_photo_text(count), reply_markup=photo_keyboard()
        )


@router.callback_query(
    F.data.startswith(prefix("pet:readypublish")),
    StateFilter(ListingWizard.photos, ListingWizard.confirm),
)
async def pet_ready_publish(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, user: User | None
) -> None:
    if user is None:
        await safe_callback_answer(callback, "Сначала отправьте /start.")
        return
    data = await state.get_data()
    raw_listing = data.get("listing_public_id")
    listing_public_id = (
        await services.parse_listing_public_id(raw_listing) if raw_listing else None
    )
    if listing_public_id is None:
        await safe_callback_answer(callback, "Черновик не найден. /addpet", show_alert=True)
        return
    _count, has_photo = await _photo_count(db, user, listing_public_id)
    if not has_photo:
        await safe_callback_answer(callback, texts.photo_required_text(), show_alert=True)
        return
    await safe_callback_answer(callback)
    if callback.message is not None:
        await _send_publish_checklist(callback.message, state, listing_public_id, data)


@router.callback_query(F.data.startswith(prefix("pet:cancel")))
async def pet_cancel(
    callback: CallbackQuery, state: FSMContext, user: User | None
) -> None:
    await state.clear()
    await safe_callback_answer(callback, "Отменено")
    if callback.message is not None:
        await callback.message.answer(texts.wizard_cancelled_text())


@router.callback_query(F.data.startswith(prefix("ml:")))
async def listing_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
    config: BotConfig,
) -> None:
    if user is None:
        await safe_callback_answer(callback, "Сначала отправьте /start.")
        return
    parts = unpack(callback.data, 3)
    if parts is None or parts[0] != "ml":
        await safe_callback_answer(callback, "Кнопка устарела.")
        return
    action, raw_id = parts[1], parts[2]
    listing_public_id = await services.parse_listing_public_id(raw_id)
    if listing_public_id is None:
        await safe_callback_answer(callback, "Объявление не найдено.")
        return
    if callback.message is None:
        await safe_callback_answer(callback)
        return
    try:
        if action == "open":
            await safe_callback_answer(callback)
            await _send_owner_listing(callback.message, db, user, listing_public_id)
            return
        if action == "photo":
            listing, animal, _has_photo = await services.owned_listing(
                db, user, listing_public_id
            )
            await state.clear()
            await state.set_state(ListingWizard.photos)
            await state.update_data(
                animal_public_id=str(animal.public_id),
                listing_public_id=str(listing.public_id),
                listing_title=listing.title,
            )
            await safe_callback_answer(callback)
            await callback.message.answer(
                texts.wizard_photo_text(0), reply_markup=photo_keyboard()
            )
            return
        if action == "pub":
            listing, animal, has_photo = await services.owned_listing(
                db, user, listing_public_id
            )
            if not has_photo:
                await safe_callback_answer(
                    callback, texts.photo_required_text(), show_alert=True
                )
                return
            await safe_callback_answer(callback)
            await _send_publish_checklist(
                callback.message,
                state,
                listing.public_id,
                {"listing_title": listing.title},
            )
            return
        if action == "pubok":
            listing = await services.publish_listing(db, user, listing_public_id)
            await state.clear()
            await safe_callback_answer(callback, "Готово")
            await callback.message.answer(
                texts.listing_published_text(
                    listing.title, listing.status, listing.moderation_reason
                )
            )
            return
        if action == "pause":
            await services.pause_listing(db, user, listing_public_id)
            await safe_callback_answer(callback, "Приостановлено")
            await _send_owner_listing(callback.message, db, user, listing_public_id)
            return
        if action == "sold":
            await services.mark_sold(db, user, listing_public_id)
            await safe_callback_answer(callback, "Отмечено как переданное")
            await _send_owner_listing(callback.message, db, user, listing_public_id)
            return
        if action == "archive":
            await services.archive_listing(db, user, listing_public_id)
            await safe_callback_answer(callback, "В архиве")
            await _send_owner_listing(callback.message, db, user, listing_public_id)
            return
    except AppError as exc:
        await safe_callback_answer(callback, exc.message, show_alert=True)
        return
    await safe_callback_answer(callback)
