from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import TelegramMethod
from aiogram.types import (
    CallbackQuery,
    Chat,
    Message,
    Update,
)
from aiogram.types import (
    User as TelegramUser,
)
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from zooffer_bot.callbacks import pack, unpack
from zooffer_bot.config import load_config
from zooffer_bot.dispatcher import build_dispatcher
from zooffer_bot.notifications import run_once
from zooffer_bot.services import link_telegram_chat
from zooffer_bot.webhook import SECRET_HEADER, create_webhook_app

from tests.helpers import make_published_listing, register
from zooffer.db.models import (
    AuthIdentity,
    DailyQuotaUsage,
    Notification,
    NotificationDelivery,
    NotificationPreference,
    Profile,
    TelegramChat,
    User,
    UserPrivateData,
)
from zooffer.db.session import SessionLocal, dispose_engine
from zooffer.main import app
from zooffer.services import auth_service

TELEGRAM_USER_ID = 9_000_001


class FakeSession(BaseSession):
    """Minimal Telegram Bot API double that records outgoing calls."""

    def __init__(self) -> None:
        super().__init__()
        self.methods: list[TelegramMethod[Any]] = []
        self._message_id = 100

    async def close(self) -> None:
        return None

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[Any],
        timeout: int | None = None,  # noqa: ASYNC109 - mirrors BaseSession
    ) -> Any:
        self.methods.append(method)
        name = type(method).__name__
        if name in {
            "SendMessage",
            "SendPhoto",
            "EditMessageReplyMarkup",
            "EditMessageText",
        }:
            self._message_id += 1
            raw_chat = getattr(method, "chat_id", 1)
            try:
                chat_id = int(raw_chat)
            except (TypeError, ValueError):
                chat_id = 1
            return Message(
                message_id=self._message_id,
                date=datetime.now(UTC),
                chat=Chat(id=chat_id, type="private"),
                text=getattr(method, "text", None),
            )
        if name == "GetMe":
            return TelegramUser(id=1, is_bot=True, first_name="Zooffer")
        return True

    async def stream_content(
        self,
        url: str,
        headers: dict[str, Any] | None = None,
        timeout: int = 30,  # noqa: ASYNC109 - mirrors BaseSession
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> AsyncIterable[bytes]:
        yield b""

    def outgoing_text(self) -> str:
        parts: list[str] = []
        for method in self.methods:
            text = getattr(method, "text", None) or getattr(method, "caption", None)
            if text:
                parts.append(str(text))
        return "\n".join(parts)


@pytest_asyncio.fixture(autouse=True)
async def dispose_bot_engine() -> AsyncIterator[None]:
    """The bot uses the process-wide engine; close pooled connections per loop."""
    yield
    await dispose_engine()


@pytest_asyncio.fixture
async def fake_bot() -> AsyncIterator[tuple[Bot, FakeSession]]:
    session = FakeSession()
    bot = Bot(
        token="123456:TEST_TOKEN_FOR_UNIT_TESTS_ONLY",
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    yield bot, session
    await bot.session.close()


@pytest.fixture(scope="session")
def dispatcher() -> Dispatcher:
    return build_dispatcher(load_config(), storage=MemoryStorage())


def _message(
    text: str,
    *,
    chat_id: int = TELEGRAM_USER_ID,
    telegram_id: int = TELEGRAM_USER_ID,
) -> Message:
    return Message(
        message_id=1,
        date=datetime.now(UTC),
        chat=Chat(id=chat_id, type="private"),
        from_user=TelegramUser(
            id=telegram_id, is_bot=False, first_name="Иван", username="private_tg_name"
        ),
        text=text,
    )


def _callback_message(chat_id: int = TELEGRAM_USER_ID) -> Message:
    return Message(
        message_id=2,
        date=datetime.now(UTC),
        chat=Chat(id=chat_id, type="private"),
        text="Кнопка",
    )


def _callback(
    data: str,
    *,
    chat_id: int = TELEGRAM_USER_ID,
    telegram_id: int = TELEGRAM_USER_ID,
    callback_id: str = "cb-1",
) -> CallbackQuery:
    return CallbackQuery(
        id=callback_id,
        from_user=TelegramUser(id=telegram_id, is_bot=False, first_name="Иван"),
        chat_instance="chat-instance",
        message=_callback_message(chat_id),
        data=data,
    )


async def _feed(dispatcher: Dispatcher, bot: Bot, update: Update) -> None:
    await dispatcher.feed_update(bot, update)


async def test_onboarding_creates_consented_account_and_chat(
    dispatcher: Dispatcher, fake_bot: tuple[Bot, FakeSession]
) -> None:
    bot, session = fake_bot
    await _feed(
        dispatcher,
        bot,
        Update(update_id=1, message=_message("/start")),
    )
    assert "Добро пожаловать в Zooffer" in session.outgoing_text()

    await _feed(
        dispatcher,
        bot,
        Update(
            update_id=2,
            callback_query=_callback(pack("onb", "accept"), callback_id="cb-consent"),
        ),
    )
    await _feed(
        dispatcher,
        bot,
        Update(update_id=3, message=_message("Иван")),
    )

    async with SessionLocal() as db:
        identity = await db.scalar(
            select(AuthIdentity).where(AuthIdentity.provider_user_id == str(TELEGRAM_USER_ID))
        )
        assert identity is not None
        user = await db.get(User, identity.user_id)
        assert user is not None and user.status == "active"
        chat = await db.scalar(
            select(TelegramChat).where(TelegramChat.user_id == user.id)
        )
        assert chat is not None and chat.chat_id == str(TELEGRAM_USER_ID)
        profile = await db.get(Profile, user.id)
        assert profile is not None and profile.public_first_name == "Иван"
    assert "Telegram" not in (session.outgoing_text().split("Добро пожаловать")[0] or "")


async def test_link_token_requires_explicit_bot_confirmation(
    dispatcher: Dispatcher,
    fake_bot: tuple[Bot, FakeSession],
    registered_client: AsyncClient,
) -> None:
    bot, session = fake_bot
    user = (await registered_client.get("/api/v1/auth/me")).json()["user"]
    async with SessionLocal() as db:
        db_user = await db.scalar(select(User).where(User.public_id == UUID(user["public_id"])))
        assert db_user is not None
        token, _expires = await auth_service.create_link_token(db, db_user.id)

    await _feed(
        dispatcher,
        bot,
        Update(
            update_id=10,
            message=_message(f"/start link_{token}", telegram_id=9_100_001, chat_id=9_100_001),
        ),
    )
    async with SessionLocal() as db:
        identity = await db.scalar(
            select(AuthIdentity).where(AuthIdentity.provider_user_id == "9100001")
        )
        assert identity is None
    assert "Подтвердите привязку" in session.outgoing_text()

    await _feed(
        dispatcher,
        bot,
        Update(
            update_id=11,
            callback_query=_callback(
                pack("link", "confirm"), telegram_id=9_100_001, chat_id=9_100_001
            ),
        ),
    )
    async with SessionLocal() as db:
        identity = await db.scalar(
            select(AuthIdentity).where(AuthIdentity.provider_user_id == "9100001")
        )
        assert identity is not None and identity.user_id == db_user.id
        chat = await db.scalar(
            select(TelegramChat).where(TelegramChat.user_id == db_user.id)
        )
        assert chat is not None

    # The token is single use: a second confirmation cannot bind another Telegram ID.
    await _feed(
        dispatcher,
        bot,
        Update(
            update_id=12,
            message=_message(
                f"/start link_{token}", telegram_id=9_100_002, chat_id=9_100_002
            ),
        ),
    )
    await _feed(
        dispatcher,
        bot,
        Update(
            update_id=13,
            callback_query=_callback(
                pack("link", "confirm"), telegram_id=9_100_002, chat_id=9_100_002
            ),
        ),
    )
    async with SessionLocal() as db:
        identity = await db.scalar(
            select(AuthIdentity).where(AuthIdentity.provider_user_id == "9100002")
        )
        assert identity is None


async def test_bot_swipe_uses_shared_quota(
    dispatcher: Dispatcher,
    fake_bot: tuple[Bot, FakeSession],
    registered_client: AsyncClient,
) -> None:
    bot, _session = fake_bot
    _animal, listing, _published = await make_published_listing(
        registered_client, title="Щенок для совместного теста"
    )
    listing_id = listing["public_id"]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as guest:
        guest_user = await register(
            guest, "bot-guest@example.com", first_name="Гость", last_name=None
        )
        async with SessionLocal() as db:
            db_user = await db.scalar(
                select(User).where(User.public_id == UUID(guest_user["public_id"]))
            )
            assert db_user is not None
            db.add(
                AuthIdentity(
                    id=uuid4(),
                    user_id=db_user.id,
                    provider="telegram",
                    provider_user_id=str(TELEGRAM_USER_ID),
                )
            )
            await db.commit()
        listing_id = listing["public_id"]

        await _feed(
            dispatcher,
            bot,
            Update(
                update_id=20,
                callback_query=_callback(
                    pack("sw", "like", listing_id), callback_id="cb-swipe"
                ),
            ),
        )

        feed = await guest.get("/api/v1/discovery/feed")
        assert feed.status_code == 200
        assert feed.json()["quota"]["remaining"] == 19

    async with SessionLocal() as db:
        usage = await db.scalar(
            select(DailyQuotaUsage).where(DailyQuotaUsage.user_id == db_user.id)
        )
        assert usage is not None and usage.used_count == 1


async def test_bot_texts_never_contain_private_owner_sentinels(
    dispatcher: Dispatcher,
    fake_bot: tuple[Bot, FakeSession],
    registered_client: AsyncClient,
) -> None:
    bot, session = fake_bot
    await make_published_listing(registered_client, title="Кот ищет семью")

    async with SessionLocal() as db:
        owner = await db.scalar(select(User).order_by(User.created_at))
        assert owner is not None
        private = await db.get(UserPrivateData, owner.id)
        assert private is not None
        private.phone_encrypted = "+7 999 111-22-33"
        private.telegram_username_encrypted = "secret_owner_username"
        await db.commit()

        viewer = await auth_service.create_telegram_bot_user(
            db,
            telegram_id="9200001",
            public_first_name="Зритель",
            accepted_terms=True,
            accepted_privacy=True,
        )
        await link_telegram_chat(db, viewer, chat_id=9_200_001)
    await _feed(
        dispatcher,
        bot,
        Update(
            update_id=30,
            message=_message("/swipe", telegram_id=9_200_001, chat_id=9_200_001),
        ),
    )
    sent = session.outgoing_text()
    assert "Кот ищет семью" in sent
    assert "Анна" in sent
    for sentinel in ("+7 999 111-22-33", "secret_owner_username", "9200001"):
        assert sentinel not in sent


async def test_webhook_rejects_forged_secret_and_deduplicates(
    dispatcher: Dispatcher, fake_bot: tuple[Bot, FakeSession]
) -> None:
    bot, _session = fake_bot
    config = load_config()
    webhook = create_webhook_app(dispatcher, bot, config)
    payload = Update(
        update_id=777, edited_message=_message("edited")
    ).model_dump_json()

    async with AsyncClient(
        transport=ASGITransport(app=webhook), base_url="http://testserver"
    ) as http:
        forged = await http.post(
            config.webhook_path,
            content=payload,
            headers={SECRET_HEADER: "wrong"},
        )
        assert forged.status_code == 403

        headers = {SECRET_HEADER: config.webhook_secret}
        first = await http.post(config.webhook_path, content=payload, headers=headers)
        assert first.status_code == 200
        assert first.json()["ok"] is True
        second = await http.post(config.webhook_path, content=payload, headers=headers)
        assert second.status_code == 200
        assert second.json().get("duplicate") is True


async def test_notifications_respect_preferences_and_quiet_hours(
    fake_bot: tuple[Bot, FakeSession],
    registered_client: AsyncClient,
) -> None:
    bot, session = fake_bot
    user_payload = (await registered_client.get("/api/v1/auth/me")).json()["user"]
    async with SessionLocal() as db:
        user = await db.scalar(
            select(User).where(User.public_id == UUID(user_payload["public_id"]))
        )
        assert user is not None
        db.add(TelegramChat(id=uuid4(), user_id=user.id, chat_id="9300001"))
        db.add(
            Notification(
                id=uuid4(),
                user_id=user.id,
                category="messages",
                title="Новое сообщение",
                body="Вам написали.",
            )
        )
        db.add(
            NotificationPreference(
                user_id=user.id,
                category="messages",
                telegram=False,
            )
        )
        await db.commit()
        user_id = user.id

    async with SessionLocal() as db:
        outcome = await run_once(db, bot, load_config())
    assert outcome.skipped == 1

    async with SessionLocal() as db:
        delivery = await db.scalar(select(NotificationDelivery))
        assert delivery is not None and delivery.status == "skipped"
        preference = await db.get(NotificationPreference, (user_id, "messages"))
        assert preference is not None
        preference.telegram = True
        db.add(
            Notification(
                id=uuid4(),
                user_id=user_id,
                category="messages",
                title="Новое сообщение",
                body="Вам ответили.",
            )
        )
        await db.commit()

    async with SessionLocal() as db:
        outcome = await run_once(db, bot, load_config())
    assert outcome.sent == 1
    assert "Новое сообщение" in session.outgoing_text()

    async with SessionLocal() as db:
        now = datetime.now(UTC)
        moscow_hour = now.astimezone(ZoneInfo("Europe/Moscow")).hour
        db.add(
            Notification(
                id=uuid4(),
                user_id=user_id,
                category="matches",
                title="Новое совпадение",
                body="Взаимная симпатия.",
            )
        )
        db.add(
            NotificationPreference(
                user_id=user_id,
                category="matches",
                telegram=True,
                quiet_from=moscow_hour,
                quiet_to=(moscow_hour + 1) % 24,
            )
        )
        await db.commit()

    async with SessionLocal() as db:
        outcome = await run_once(db, bot, load_config())
    assert outcome.deferred == 1
    async with SessionLocal() as db:
        delivery = await db.scalar(
            select(NotificationDelivery)
            .join(Notification)
            .where(Notification.category == "matches")
        )
        assert delivery is not None and delivery.status == "deferred"

        preference = await db.get(NotificationPreference, (user_id, "matches"))
        assert preference is not None
        preference.quiet_from = None
        preference.quiet_to = None
        await db.commit()

    async with SessionLocal() as db:
        outcome = await run_once(
            db, bot, load_config(), now=datetime.now(UTC) + timedelta(minutes=1)
        )
    assert outcome.sent == 1


def test_callback_payloads_are_signed_and_size_limited() -> None:
    data = pack("sw", "like", str(uuid4()))
    assert len(data.encode()) <= 64
    assert unpack(data, 3) == ("sw", "like", data.split(":")[3])
    tampered = data[:-1] + ("A" if data[-1] != "A" else "B")
    assert unpack(tampered, 3) is None
    assert unpack(None, 2) is None
    with pytest.raises(ValueError):
        pack("menu", "x" * 80)
