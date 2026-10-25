from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from zooffer.core.errors import AppError
from zooffer.db.models import User
from zooffer.schemas.messaging import ConversationDetailView

from .. import services, texts
from ..callbacks import prefix, unpack
from ..config import BotConfig
from ..keyboards import chat_keyboard, chats_keyboard
from ..states import ChatFlow
from .common import ensure_onboarded, safe_callback_answer

router = Router(name="chats")


def _conversation_text(detail: ConversationDetailView) -> str:
    messages = [(item.body, item.mine) for item in detail.messages if item.body]
    return texts.conversation_text(detail.conversation, messages)


async def show_chats(
    message: Message,
    db: AsyncSession,
    user: User,
) -> None:
    listing = await services.conversations(db, user)
    labels: list[tuple[str, str]] = []
    for item in listing.items:
        name = (item.counterpart.display_name or "Владелец").strip()
        if item.listing:
            name = f"{name} · {item.listing.title}"
        if item.unread_count:
            name = f"{name} ({item.unread_count})"
        labels.append((str(item.public_id), name))
    await message.answer(
        texts.chats_text(len(listing.items)),
        reply_markup=chats_keyboard(labels),
    )


async def _open_conversation(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User,
    conversation_public_id,
    *,
    prompt: bool = False,
) -> None:
    detail = await services.conversation(db, user, conversation_public_id)
    await services.mark_conversation_read(db, user, conversation_public_id)
    await state.set_state(ChatFlow.writing)
    await state.update_data(conversation_public_id=str(conversation_public_id))
    await message.answer(
        _conversation_text(detail),
        reply_markup=chat_keyboard(str(conversation_public_id)),
    )
    if prompt:
        await message.answer("Напишите сообщение одним текстом. /cancel — выйти.")


@router.message(Command("chats"))
async def cmd_chats(
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
    await show_chats(message, db, user)


@router.callback_query(F.data.startswith(prefix("ch:")))
async def chat_callback(
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
    if parts is None or parts[0] != "ch":
        await safe_callback_answer(callback, "Кнопка устарела.")
        return
    action, raw_id = parts[1], parts[2]
    if callback.message is None:
        await safe_callback_answer(callback)
        return
    conversation_public_id = await services.parse_listing_public_id(raw_id)
    if conversation_public_id is None:
        await safe_callback_answer(callback, "Диалог не найден.")
        return

    if action == "inquire":
        try:
            detail = await services.start_inquiry(db, user, conversation_public_id)
        except AppError as exc:
            await safe_callback_answer(callback, exc.message, show_alert=True)
            return
        await safe_callback_answer(callback, "Чат открыт")
        await _open_conversation(
            callback.message,
            state,
            db,
            user,
            detail.conversation.public_id,
            prompt=True,
        )
        return

    if action not in {"open", "reply"}:
        await safe_callback_answer(callback)
        return
    try:
        await _open_conversation(
            callback.message,
            state,
            db,
            user,
            conversation_public_id,
            prompt=action == "reply",
        )
    except AppError as exc:
        await safe_callback_answer(callback, exc.message, show_alert=True)
        return
    await safe_callback_answer(callback)


@router.message(ChatFlow.writing, F.text, ~F.text.startswith("/"))
async def chat_message(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
) -> None:
    if user is None:
        await state.clear()
        await message.answer("Сначала отправьте /start.")
        return
    data = await state.get_data()
    raw_id = data.get("conversation_public_id")
    conversation_public_id = (
        await services.parse_listing_public_id(raw_id) if isinstance(raw_id, str) else None
    )
    if conversation_public_id is None:
        await state.clear()
        await message.answer("Диалог не найден. Откройте /chats.")
        return
    try:
        await services.send_message(db, user, conversation_public_id, message.text or "")
    except AppError as exc:
        await message.answer(exc.message, reply_markup=chat_keyboard(str(conversation_public_id)))
        return
    await message.answer(
        "Сообщение отправлено.",
        reply_markup=chat_keyboard(str(conversation_public_id)),
    )
