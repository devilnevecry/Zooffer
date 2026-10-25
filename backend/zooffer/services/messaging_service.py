from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from zooffer.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from zooffer.core.rate_limit import limiter
from zooffer.core.utils import utcnow
from zooffer.db.models import (
    Animal,
    AnimalPhoto,
    Block,
    Conversation,
    ConversationParticipant,
    Listing,
    Message,
    Notification,
    Profile,
    User,
)
from zooffer.schemas.messaging import (
    ConversationDetailView,
    ConversationListingView,
    ConversationListView,
    ConversationSummaryView,
    LastMessageView,
    MessagePageView,
    MessageView,
    PublicCounterpartyView,
)
from zooffer.services.listing_service import PUBLISHED, decode_cursor, display_name, encode_cursor
from zooffer.services.media import media_url, thumb_key_for

MAX_MESSAGE_LENGTH = 4000
MESSAGE_RATE_LIMIT = 30
MESSAGE_RATE_WINDOW = 60
INQUIRY_DAILY_LIMIT = 10


def _message_view(message: Message, user_id: UUID) -> MessageView:
    return MessageView(
        id=message.id,
        body="" if message.deleted_by_sender and message.sender_id != user_id else message.body,
        mine=message.sender_id == user_id,
        edited_at=message.edited_at,
        created_at=message.created_at,
    )


async def _participant(
    db: AsyncSession, user_id: UUID, conversation_public_id: UUID
) -> tuple[Conversation, ConversationParticipant]:
    row = (
        await db.execute(
            select(Conversation, ConversationParticipant)
            .join(
                ConversationParticipant,
                ConversationParticipant.conversation_id == Conversation.id,
            )
            .where(
                Conversation.public_id == conversation_public_id,
                ConversationParticipant.user_id == user_id,
            )
        )
    ).first()
    if row is None:
        raise NotFoundError("Диалог не найден", code="conversation_not_found")
    return row[0], row[1]


async def _counterpart_id(db: AsyncSession, conversation_id: UUID, user_id: UUID) -> UUID | None:
    return await db.scalar(
        select(ConversationParticipant.user_id).where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id != user_id,
        )
    )


async def _blocked_between(db: AsyncSession, a: UUID, b: UUID) -> bool:
    found = await db.scalar(
        select(Block.id).where(
            or_(
                and_(Block.blocker_id == a, Block.blocked_id == b),
                and_(Block.blocker_id == b, Block.blocked_id == a),
            )
        )
    )
    return found is not None


async def _counterpart_name(db: AsyncSession, conversation_id: UUID, user_id: UUID) -> str | None:
    other = await _counterpart_id(db, conversation_id, user_id)
    if other is None:
        return None
    profile = await db.get(Profile, other)
    return display_name(profile)


async def _listing_view(
    db: AsyncSession, listing_id: UUID | None
) -> ConversationListingView | None:
    if listing_id is None:
        return None
    row = (
        await db.execute(
            select(Listing, Animal)
            .join(Animal, Animal.id == Listing.animal_id)
            .where(Listing.id == listing_id)
        )
    ).first()
    if row is None:
        return None
    listing, animal = row
    photo = await db.scalar(
        select(AnimalPhoto)
        .where(AnimalPhoto.animal_id == animal.id)
        .order_by(AnimalPhoto.is_primary.desc(), AnimalPhoto.position.asc())
        .limit(1)
    )
    return ConversationListingView(
        public_id=listing.public_id,
        slug=listing.slug,
        title=listing.title,
        animal_name=animal.name,
        primary_photo_url=media_url(thumb_key_for(photo.storage_key)) if photo else None,
    )


async def _last_message(db: AsyncSession, conversation_id: UUID, user_id: UUID) -> Message | None:
    return await db.scalar(
        select(Message)
        .where(Message.conversation_id == conversation_id, Message.deleted_at.is_(None))
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(1)
    )


async def _unread_count(
    db: AsyncSession, conversation_id: UUID, user_id: UUID, last_read_at: datetime | None
) -> int:
    stmt = (
        select(func.count())
        .select_from(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.deleted_at.is_(None),
            Message.sender_id != user_id,
        )
    )
    if last_read_at is not None:
        stmt = stmt.where(Message.created_at > last_read_at)
    return int(await db.scalar(stmt) or 0)


async def _summary(
    db: AsyncSession, conversation: Conversation, participant: ConversationParticipant
) -> ConversationSummaryView:
    user_id = participant.user_id
    counterpart_id = await _counterpart_id(db, conversation.id, user_id)
    blocked = (
        await _blocked_between(db, user_id, counterpart_id) if counterpart_id is not None else False
    )
    name = await _counterpart_name(db, conversation.id, user_id)
    last = await _last_message(db, conversation.id, user_id)
    unread = await _unread_count(db, conversation.id, user_id, participant.last_read_at)
    return ConversationSummaryView(
        public_id=conversation.public_id,
        conversation_type=conversation.conversation_type,
        counterpart=PublicCounterpartyView(display_name=name),
        listing=await _listing_view(db, conversation.listing_id),
        last_message=(
            LastMessageView(
                body=last.body[:280],
                mine=last.sender_id == user_id,
                created_at=last.created_at,
            )
            if last
            else None
        ),
        unread_count=unread,
        last_message_at=conversation.last_message_at,
        updated_at=conversation.updated_at,
        blocked=blocked,
    )


async def list_conversations(db: AsyncSession, user_id: UUID) -> ConversationListView:
    rows = (
        await db.execute(
            select(Conversation, ConversationParticipant)
            .join(
                ConversationParticipant,
                ConversationParticipant.conversation_id == Conversation.id,
            )
            .where(ConversationParticipant.user_id == user_id)
            .order_by(
                func.coalesce(Conversation.last_message_at, Conversation.created_at).desc(),
                Conversation.id.desc(),
            )
        )
    ).all()
    return ConversationListView(items=[await _summary(db, c, p) for c, p in rows])


def _encode_message_cursor(message: Message) -> str:
    return encode_cursor({"c": message.created_at.isoformat(), "i": str(message.id)})


async def list_messages(
    db: AsyncSession,
    user_id: UUID,
    conversation_public_id: UUID,
    *,
    limit: int = 30,
    cursor: str | None = None,
) -> MessagePageView:
    conversation, participant = await _participant(db, user_id, conversation_public_id)
    stmt = select(Message).where(
        Message.conversation_id == conversation.id, Message.deleted_at.is_(None)
    )
    if cursor:
        data = decode_cursor(cursor)
        try:
            created = datetime.fromisoformat(str(data["c"]))
            message_id = UUID(str(data["i"]))
        except (KeyError, ValueError) as exc:
            raise ValidationAppError("Некорректный курсор", code="invalid_cursor") from exc
        if created.tzinfo is None:
            created = created.replace(tzinfo=participant.joined_at.tzinfo)
        stmt = stmt.where(
            or_(
                Message.created_at < created,
                and_(Message.created_at == created, Message.id < message_id),
            )
        )
    rows = (
        await db.scalars(
            stmt.order_by(Message.created_at.desc(), Message.id.desc()).limit(limit + 1)
        )
    ).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = _encode_message_cursor(rows[-1]) if rows and has_more else None
    return MessagePageView(
        items=[_message_view(m, user_id) for m in reversed(rows)],
        next_cursor=next_cursor,
        has_more=has_more,
    )


async def get_conversation(
    db: AsyncSession,
    user_id: UUID,
    conversation_public_id: UUID,
    *,
    limit: int = 30,
    cursor: str | None = None,
) -> ConversationDetailView:
    conversation, participant = await _participant(db, user_id, conversation_public_id)
    page = await list_messages(db, user_id, conversation_public_id, limit=limit, cursor=cursor)
    return ConversationDetailView(
        conversation=await _summary(db, conversation, participant),
        messages=page.items,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


async def mark_read(
    db: AsyncSession, user_id: UUID, conversation_public_id: UUID
) -> ConversationSummaryView:
    conversation, participant = await _participant(db, user_id, conversation_public_id)
    participant.last_read_at = utcnow()
    await db.commit()
    return await _summary(db, conversation, participant)


async def _notify(
    db: AsyncSession,
    user_id: UUID,
    *,
    category: str,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> None:
    db.add(
        Notification(
            id=uuid4(),
            user_id=user_id,
            category=category,
            title=title,
            body=body[:600],
            data=data,
        )
    )


async def send_message(
    db: AsyncSession,
    user: User,
    conversation_public_id: UUID,
    body: str,
) -> MessageView:
    conversation, _participant_row = await _participant(db, user.id, conversation_public_id)
    if conversation.closed_at is not None:
        raise ForbiddenError("Диалог закрыт", code="conversation_closed")
    counterpart_id = await _counterpart_id(db, conversation.id, user.id)
    if counterpart_id is None:
        raise ConflictError("Диалог повреждён", code="conversation_invalid")
    if await _blocked_between(db, user.id, counterpart_id):
        raise ForbiddenError("Диалог недоступен", code="blocked")

    cleaned = body.replace("\r\n", "\n").strip()
    if not cleaned:
        raise ValidationAppError("Сообщение не может быть пустым", code="empty_message")
    if len(cleaned) > MAX_MESSAGE_LENGTH:
        raise ValidationAppError("Сообщение слишком длинное", code="message_too_long")

    await limiter.hit(
        f"message:{user.id}", limit=MESSAGE_RATE_LIMIT, window_seconds=MESSAGE_RATE_WINDOW
    )

    duplicate = await db.scalar(
        select(Message.id).where(
            Message.conversation_id == conversation.id,
            Message.sender_id == user.id,
            Message.body == cleaned,
            Message.created_at > utcnow() - timedelta(seconds=15),
        )
    )
    if duplicate is not None:
        raise ConflictError("Это сообщение уже отправлено", code="duplicate_message")

    now = utcnow()
    message = Message(
        id=uuid4(),
        conversation_id=conversation.id,
        sender_id=user.id,
        body=cleaned,
        created_at=now,
    )
    conversation.last_message_at = now
    db.add(message)
    await _notify(
        db,
        counterpart_id,
        category="messages",
        title="Новое сообщение",
        body=cleaned,
        data={"conversation_public_id": str(conversation.public_id)},
    )
    await db.commit()
    return _message_view(message, user.id)


async def start_inquiry(
    db: AsyncSession,
    user: User,
    listing_public_id: UUID,
    message: str | None = None,
) -> ConversationDetailView:
    listing = await db.scalar(
        select(Listing).where(Listing.public_id == listing_public_id, Listing.status == PUBLISHED)
    )
    if listing is None:
        raise NotFoundError("Объявление не найдено", code="listing_not_found")
    if listing.owner_id == user.id:
        raise ValidationAppError("Нельзя написать по собственному объявлению", code="own_listing")
    if await _blocked_between(db, user.id, listing.owner_id):
        raise ForbiddenError("Действие недоступно", code="blocked")

    existing = await db.scalar(
        select(Conversation)
        .join(
            ConversationParticipant,
            ConversationParticipant.conversation_id == Conversation.id,
        )
        .where(
            Conversation.conversation_type == "inquiry",
            Conversation.listing_id == listing.id,
            ConversationParticipant.user_id == user.id,
        )
        .order_by(Conversation.created_at.desc())
        .limit(1)
    )
    if existing is not None:
        return await get_conversation(db, user.id, existing.public_id)

    await limiter.hit(f"inquiry:{user.id}", limit=INQUIRY_DAILY_LIMIT, window_seconds=86_400)

    now = utcnow()
    conversation = Conversation(
        id=uuid4(),
        public_id=uuid4(),
        conversation_type="inquiry",
        listing_id=listing.id,
        animal_id=listing.animal_id,
        last_message_at=now if message else None,
    )
    db.add(conversation)
    await db.flush()
    db.add_all(
        [
            ConversationParticipant(conversation_id=conversation.id, user_id=user.id),
            ConversationParticipant(conversation_id=conversation.id, user_id=listing.owner_id),
        ]
    )
    if message:
        cleaned = message.strip()
        if cleaned:
            db.add(
                Message(
                    id=uuid4(),
                    conversation_id=conversation.id,
                    sender_id=user.id,
                    body=cleaned[:MAX_MESSAGE_LENGTH],
                    created_at=now,
                )
            )
    await _notify(
        db,
        listing.owner_id,
        category="inquiries",
        title="Новый вопрос по объявлению",
        body=message[:240] if message else listing.title,
        data={"conversation_public_id": str(conversation.public_id)},
    )
    await db.commit()
    return await get_conversation(db, user.id, conversation.public_id)


async def block_counterpart(db: AsyncSession, user: User, conversation_public_id: UUID) -> None:
    conversation, _participant_row = await _participant(db, user.id, conversation_public_id)
    counterpart_id = await _counterpart_id(db, conversation.id, user.id)
    if counterpart_id is None:
        raise NotFoundError("Пользователь не найден", code="counterpart_not_found")
    if not await _blocked_between(db, user.id, counterpart_id):
        db.add(Block(id=uuid4(), blocker_id=user.id, blocked_id=counterpart_id))
    await db.commit()


async def unblock_counterpart(db: AsyncSession, user: User, conversation_public_id: UUID) -> None:
    conversation, _participant_row = await _participant(db, user.id, conversation_public_id)
    counterpart_id = await _counterpart_id(db, conversation.id, user.id)
    if counterpart_id is None:
        raise NotFoundError("Пользователь не найден", code="counterpart_not_found")
    await db.execute(
        delete(Block).where(Block.blocker_id == user.id, Block.blocked_id == counterpart_id)
    )
    await db.commit()
