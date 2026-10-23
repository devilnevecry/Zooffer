from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from zooffer.core.errors import AppError
from zooffer.db.models import User

from .. import services, texts
from ..callbacks import prefix, unpack
from ..config import BotConfig
from ..keyboards import support_cancel
from ..states import SupportFlow
from .common import ensure_onboarded, safe_callback_answer

router = Router(name="support")


async def begin_support(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(SupportFlow.subject)
    await state.update_data(support_subject=None)
    await message.answer(texts.support_intro_text())
    await message.answer(texts.support_subject_prompt(), reply_markup=support_cancel())


@router.message(Command("support"))
async def cmd_support(
    message: Message,
    state: FSMContext,
    user: User | None,
    config: BotConfig,
) -> None:
    if user is None:
        if await ensure_onboarded(message, user, state, config):
            return
        return
    await begin_support(message, state)


@router.message(SupportFlow.subject, F.text)
async def support_subject(
    message: Message,
    state: FSMContext,
    user: User | None,
) -> None:
    if user is None:
        await state.clear()
        return
    value = " ".join((message.text or "").split())
    if len(value) < 3 or len(value) > 160:
        await message.answer(
            "Тема должна быть от 3 до 160 символов.", reply_markup=support_cancel()
        )
        return
    await state.update_data(support_subject=value)
    await state.set_state(SupportFlow.message)
    await message.answer(texts.support_message_prompt(), reply_markup=support_cancel())


@router.message(SupportFlow.message, F.text)
async def support_message(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
) -> None:
    if user is None:
        await state.clear()
        return
    value = (message.text or "").strip()
    if len(value) < 10 or len(value) > 5000:
        await message.answer(
            "Опишите ситуацию текстом от 10 до 5000 символов.",
            reply_markup=support_cancel(),
        )
        return
    data = await state.get_data()
    subject = str(data.get("support_subject") or "")
    try:
        ticket = await services.create_support_ticket(
            db, user, subject=subject, message=value
        )
    except AppError as exc:
        await message.answer(exc.message, reply_markup=support_cancel())
        return
    await state.clear()
    await message.answer(texts.support_created_text(str(ticket.public_id)))


@router.callback_query(F.data.startswith(prefix("sup:")))
async def support_cancel_callback(
    callback: CallbackQuery, state: FSMContext
) -> None:
    parts = unpack(callback.data, 2)
    if parts is None or parts[0] != "sup":
        await safe_callback_answer(callback, "Кнопка устарела.")
        return
    await state.clear()
    await safe_callback_answer(callback, "Отменено")
    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(texts.support_cancelled_text())
