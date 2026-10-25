from __future__ import annotations

import hashlib
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from zooffer.core.enums import SwipeAction, SwipeSource
from zooffer.core.errors import ValidationAppError
from zooffer.core.rate_limit import limiter
from zooffer.db.models import (
    Animal,
    AnimalPhoto,
    CampaignAttribution,
    City,
    Listing,
    NotificationPreference,
    Plan,
    Profile,
    Referral,
    TelegramChat,
    User,
)
from zooffer.schemas.account import PlanView, SubscriptionView
from zooffer.schemas.discovery import SwipeResponse
from zooffer.schemas.messaging import ConversationDetailView, ConversationListView
from zooffer.schemas.public import PublicListingCardView, PublicListingView
from zooffer.services import (
    account_service,
    billing_service,
    listing_service,
    messaging_service,
    quota_service,
    swipe_service,
)
from zooffer.services.listing_service import ListingFilters, display_name

NOTIFICATION_CATEGORIES = (
    "matches",
    "messages",
    "inquiries",
    "listing_moderation",
    "subscriptions",
    "partners",
    "support",
    "security",
)

SUPPORT_RATE_LIMIT = 5
SUPPORT_RATE_WINDOW = 3600


async def get_profile(db: AsyncSession, user: User) -> Profile | None:
    return await db.get(Profile, user.id)


async def public_name_for(db: AsyncSession, user: User) -> str:
    profile = await get_profile(db, user)
    return display_name(profile) or "Владелец"


async def city_name_for(db: AsyncSession, user: User) -> str | None:
    profile = await get_profile(db, user)
    if profile is None or profile.city_id is None:
        return None
    city = await db.get(City, profile.city_id)
    return city.name if city else None


async def link_telegram_chat(
    db: AsyncSession,
    user: User,
    *,
    chat_id: int | str,
    notifications_enabled: bool = True,
) -> TelegramChat:
    chat = await db.scalar(select(TelegramChat).where(TelegramChat.user_id == user.id))
    if chat is None:
        chat = TelegramChat(
            id=uuid4(),
            user_id=user.id,
            chat_id=str(chat_id),
            notifications_enabled=notifications_enabled,
        )
        db.add(chat)
    else:
        chat.chat_id = str(chat_id)
        chat.notifications_enabled = notifications_enabled
    await db.commit()
    return chat


async def telegram_notifications_enabled(db: AsyncSession, user_id: UUID) -> bool:
    value = await db.scalar(
        select(TelegramChat.notifications_enabled).where(TelegramChat.user_id == user_id)
    )
    return bool(value)


async def toggle_telegram_notifications(db: AsyncSession, user_id: UUID) -> bool:
    chat = await db.scalar(select(TelegramChat).where(TelegramChat.user_id == user_id))
    if chat is None:
        return False
    chat.notifications_enabled = not chat.notifications_enabled
    await db.commit()
    return chat.notifications_enabled


async def set_all_telegram_preferences(db: AsyncSession, user_id: UUID, enabled: bool) -> None:
    """Toggle Telegram delivery for every category (used by /stop and /settings)."""
    chat = await db.scalar(select(TelegramChat).where(TelegramChat.user_id == user_id))
    if chat is not None:
        chat.notifications_enabled = enabled
    for category in NOTIFICATION_CATEGORIES:
        row = await db.get(NotificationPreference, (user_id, category))
        if row is None:
            row = NotificationPreference(user_id=user_id, category=category)
            db.add(row)
        row.telegram = enabled
    await db.commit()


async def next_feed_item(
    db: AsyncSession, user: User, *, limit: int = 1
) -> tuple[list[PublicListingCardView], int, bool]:
    quota = await quota_service.get_quota(db, user.id)
    items, _cursor, _has_more = await listing_service.search_public_listings(
        db,
        ListingFilters(),
        limit=limit,
        exclude_owner_id=user.id,
        exclude_swiped_for=user.id,
        exclude_blocked_for=user.id,
    )
    return items, quota.remaining, quota.unlimited


async def get_public_listing(db: AsyncSession, value: str) -> PublicListingView:
    return await listing_service.get_public_listing(db, value)


def swipe_request_id(user_id: UUID, listing_public_id: UUID) -> str:
    digest = hashlib.sha256(f"{user_id}:{listing_public_id}".encode()).hexdigest()[:40]
    return f"bot:{digest}"


async def perform_swipe(
    db: AsyncSession,
    user: User,
    listing_public_id: UUID,
    action: SwipeAction,
) -> SwipeResponse:
    return await swipe_service.swipe(
        db,
        user,
        listing_public_id=listing_public_id,
        action=action,
        request_id=swipe_request_id(user.id, listing_public_id),
        source=SwipeSource.BOT,
    )


async def add_favorite(db: AsyncSession, user: User, listing_public_id: UUID) -> None:
    await swipe_service.add_favorite(db, user, listing_public_id)


async def remove_favorite(db: AsyncSession, user: User, listing_public_id: UUID) -> None:
    await swipe_service.remove_favorite(db, user, listing_public_id)


async def favorites(db: AsyncSession, user: User) -> list[tuple[Listing, Animal]]:
    return await swipe_service.list_favorites(db, user)


async def conversations(db: AsyncSession, user: User) -> ConversationListView:
    return await messaging_service.list_conversations(db, user.id)


async def conversation(
    db: AsyncSession, user: User, conversation_public_id: UUID
) -> ConversationDetailView:
    return await messaging_service.get_conversation(db, user.id, conversation_public_id)


async def mark_conversation_read(
    db: AsyncSession, user: User, conversation_public_id: UUID
) -> None:
    await messaging_service.mark_read(db, user.id, conversation_public_id)


async def send_message(db: AsyncSession, user: User, conversation_public_id: UUID, body: str):
    return await messaging_service.send_message(db, user, conversation_public_id, body)


async def start_inquiry(
    db: AsyncSession, user: User, listing_public_id: UUID, message: str | None = None
) -> ConversationDetailView:
    return await messaging_service.start_inquiry(db, user, listing_public_id, message)


async def owned_listings(db: AsyncSession, user: User) -> list[tuple[Listing, Animal, bool]]:
    rows = (
        await db.execute(
            select(Listing, Animal)
            .join(Animal, Animal.id == Listing.animal_id)
            .where(Listing.owner_id == user.id)
            .order_by(Listing.created_at.desc())
        )
    ).all()
    result: list[tuple[Listing, Animal, bool]] = []
    for listing, animal in rows:
        photo_count = await db.scalar(
            select(func.count()).select_from(AnimalPhoto).where(AnimalPhoto.animal_id == animal.id)
        )
        result.append((listing, animal, bool(photo_count)))
    return result


async def owned_listing(
    db: AsyncSession, user: User, listing_public_id: UUID
) -> tuple[Listing, Animal, bool]:
    row = (
        await db.execute(
            select(Listing, Animal)
            .join(Animal, Animal.id == Listing.animal_id)
            .where(Listing.public_id == listing_public_id, Listing.owner_id == user.id)
        )
    ).first()
    if row is None:
        from zooffer.core.errors import NotFoundError

        raise NotFoundError("Объявление не найдено", code="listing_not_found")
    photo_count = await db.scalar(
        select(func.count()).select_from(AnimalPhoto).where(AnimalPhoto.animal_id == row[1].id)
    )
    return row[0], row[1], bool(photo_count)


async def find_city(db: AsyncSession, value: str) -> City | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    return await db.scalar(select(City).where(func.lower(City.name) == cleaned.lower()).limit(1))


async def add_photo(
    db: AsyncSession, user: User, animal_public_id: UUID, content: bytes
) -> AnimalPhoto:
    return await listing_service.add_animal_photo(db, user, animal_public_id, content)


async def publish_listing(db: AsyncSession, user: User, public_id: UUID) -> Listing:
    return await listing_service.publish_listing(db, user, public_id)


async def pause_listing(db: AsyncSession, user: User, public_id: UUID) -> Listing:
    return await listing_service.pause_listing(db, user, public_id)


async def renew_listing(db: AsyncSession, user: User, public_id: UUID) -> Listing:
    return await listing_service.renew_listing(db, user, public_id)


async def archive_listing(db: AsyncSession, user: User, public_id: UUID) -> Listing:
    return await listing_service.archive_listing(db, user, public_id)


async def mark_sold(db: AsyncSession, user: User, public_id: UUID) -> Listing:
    return await listing_service.mark_sold(db, user, public_id)


def payments_available() -> bool:
    """Telegram Stars purchase flow is not implemented yet.

    Digital goods inside Telegram must use Stars; a card-link flow would violate
    current Telegram policy and is therefore never offered here. The website and
    Mini App billing endpoints remain separate until Stars is implemented (B5).
    """
    return False


async def plan_views(db: AsyncSession) -> list[PlanView]:
    plans = (
        await db.scalars(
            select(Plan)
            .where(Plan.is_active.is_(True))
            .order_by(Plan.sort_order, Plan.price_kopecks)
        )
    ).all()
    return [
        PlanView(
            code=plan.code,
            name=plan.name,
            description=plan.description,
            price_kopecks=plan.price_kopecks,
            currency=plan.currency,
            stars_amount=plan.stars_amount,
            period_days=plan.period_days,
            entitlements=list(plan.entitlements or []),
            is_placeholder_price=plan.is_placeholder_price,
        )
        for plan in plans
    ]


async def get_subscription_view(db: AsyncSession, user: User) -> SubscriptionView:
    return await billing_service.subscription_view(db, user)


async def record_referral(db: AsyncSession, invitee: User, code: str) -> bool:
    """Attribute one referral. Codes are the inviter's opaque public UUID."""
    value = code.strip()
    if not value:
        return False
    try:
        inviter_public_id = UUID(hex=value) if len(value) == 32 else UUID(value)
    except (ValueError, AttributeError):
        return False
    inviter = await db.scalar(
        select(User).where(User.public_id == inviter_public_id, User.status == "active")
    )
    if inviter is None or inviter.id == invitee.id:
        return False
    existing = await db.scalar(select(Referral.id).where(Referral.invitee_id == invitee.id))
    if existing is not None:
        return False
    db.add(
        Referral(
            id=uuid4(),
            inviter_id=inviter.id,
            invitee_id=invitee.id,
            code=inviter.public_id.hex,
        )
    )
    await db.commit()
    return True


async def record_campaign(db: AsyncSession, user: User, parts: list[str]) -> bool:
    if not parts:
        return False
    existing = await db.scalar(
        select(CampaignAttribution.id).where(CampaignAttribution.user_id == user.id)
    )
    if existing is not None:
        return False
    values = ([*parts, "", "", ""])[:3]
    db.add(
        CampaignAttribution(
            id=uuid4(),
            user_id=user.id,
            utm_source=values[0][:120] or None,
            utm_medium=values[1][:120] or None,
            utm_campaign=values[2][:120] or None,
        )
    )
    await db.commit()
    return True


async def create_support_ticket(db: AsyncSession, user: User, *, subject: str, message: str):
    if len(subject.strip()) < 3:
        raise ValidationAppError("Тема должна быть не короче 3 символов", code="invalid_subject")
    if len(message.strip()) < 10:
        raise ValidationAppError("Опишите ситуацию подробнее", code="invalid_message")
    await limiter.hit(
        f"support:{user.id}", limit=SUPPORT_RATE_LIMIT, window_seconds=SUPPORT_RATE_WINDOW
    )
    return await account_service.create_support_ticket(
        db, user, subject=subject, message=message, channel="telegram"
    )


async def parse_listing_public_id(value: str) -> UUID | None:
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        return None
