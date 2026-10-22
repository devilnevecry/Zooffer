from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from zooffer.core.enums import Entitlement, SwipeAction, SwipeSource
from zooffer.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from zooffer.core.metrics import MATCHES, SWIPES
from zooffer.db.models import (
    Animal,
    Block,
    Conversation,
    ConversationParticipant,
    Favorite,
    Listing,
    Match,
    Swipe,
    User,
)
from zooffer.schemas.discovery import SwipeResponse
from zooffer.services import listing_service, quota_service
from zooffer.services.entitlements import get_entitlements


async def _blocked_between(db: AsyncSession, a: UUID, b: UUID) -> bool:
    found = await db.scalar(
        select(Block.id).where(
            ((Block.blocker_id == a) & (Block.blocked_id == b))
            | ((Block.blocker_id == b) & (Block.blocked_id == a))
        )
    )
    return found is not None


async def _load_target(db: AsyncSession, listing_public_id: UUID) -> tuple[Listing, Animal]:
    row = (
        await db.execute(
            select(Listing, Animal)
            .join(Animal, Animal.id == Listing.animal_id)
            .where(Listing.public_id == listing_public_id)
        )
    ).first()
    if row is None:
        raise NotFoundError("Объявление не найдено", code="listing_not_found")
    return row[0], row[1]


def _canonical_pair(a: UUID, b: UUID) -> tuple[UUID, UUID]:
    return (a, b) if str(a) < str(b) else (b, a)


async def _find_match_for_swipe(
    db: AsyncSession, user_id: UUID, target_animal_id: UUID
) -> Match | None:
    user_animals = select(Animal.id).where(Animal.owner_id == user_id)
    return await db.scalar(select(Match).where(or_matches_user(target_animal_id, user_animals)))


def or_matches_user(target_animal_id: UUID, user_animals):  # type: ignore[no-untyped-def]
    return or_(
        and_(Match.animal_a_id == target_animal_id, Match.animal_b_id.in_(user_animals)),
        and_(Match.animal_b_id == target_animal_id, Match.animal_a_id.in_(user_animals)),
    )


async def _reciprocal_like(
    db: AsyncSession, target_owner_id: UUID, target_animal: Animal, user_id: UUID
) -> tuple[Animal, Listing] | None:
    """Find the user's animal that the target owner liked, if compatible for mating."""
    rows = (
        await db.execute(
            select(Animal, Listing)
            .join(Swipe, Swipe.animal_id == Animal.id)
            .join(Listing, Listing.id == Swipe.target_id)
            .where(
                Swipe.user_id == target_owner_id,
                Swipe.action == SwipeAction.LIKE.value,
                Listing.status == listing_service.PUBLISHED,
                Listing.purpose.in_([p.value for p in listing_service.MATING_PURPOSES]),
                Animal.owner_id == user_id,
            )
        )
    ).all()
    for animal, listing in rows:
        if listing_service.compatible_for_mating(target_animal, animal):
            return animal, listing
    return None


async def _create_match_and_conversation(
    db: AsyncSession,
    *,
    target_listing: Listing,
    target_animal: Animal,
    user: User,
    partner_animal: Animal,
    partner_listing: Listing,
) -> tuple[Match, Conversation]:
    a_id, b_id = _canonical_pair(target_animal.id, partner_animal.id)
    owner_a = target_animal.owner_id if a_id == target_animal.id else partner_animal.owner_id
    owner_b = (
        partner_animal.owner_id if owner_a == target_animal.owner_id else target_animal.owner_id
    )
    conversation = Conversation(
        id=uuid4(),
        public_id=uuid4(),
        conversation_type="match",
        listing_id=target_listing.id,
        animal_id=target_animal.id,
    )
    db.add(conversation)
    await db.flush()
    db.add_all(
        [
            ConversationParticipant(conversation_id=conversation.id, user_id=owner_a),
            ConversationParticipant(conversation_id=conversation.id, user_id=owner_b),
        ]
    )
    stmt = (
        pg_insert(Match)
        .values(
            id=uuid4(),
            animal_a_id=a_id,
            animal_b_id=b_id,
            owner_a_id=owner_a,
            owner_b_id=owner_b,
            conversation_id=conversation.id,
        )
        .on_conflict_do_nothing(index_elements=[Match.animal_a_id, Match.animal_b_id])
        .returning(Match.id)
    )
    inserted = await db.scalar(stmt)
    if inserted is None:
        # Another concurrent request created the match; discard our conversation.
        await db.delete(conversation)
        existing = await db.scalar(
            select(Match).where(Match.animal_a_id == a_id, Match.animal_b_id == b_id)
        )
        if existing is None:
            raise ConflictError("Не удалось создать совпадение", code="match_conflict")
        existing_conversation = await db.get(Conversation, existing.conversation_id)
        if existing_conversation is None:
            raise ConflictError("Не удалось создать чат", code="match_conflict")
        return existing, existing_conversation
    match = await db.get(Match, inserted)
    if match is None:
        raise ConflictError("Не удалось создать совпадение", code="match_conflict")
    MATCHES.inc()
    return match, conversation


async def swipe(
    db: AsyncSession,
    user: User,
    *,
    listing_public_id: UUID,
    action: SwipeAction,
    request_id: str,
    source: SwipeSource = SwipeSource.WEB,
) -> SwipeResponse:
    target_listing, target_animal = await _load_target(db, listing_public_id)
    if target_listing.status != listing_service.PUBLISHED:
        raise NotFoundError("Объявление больше не доступно", code="listing_not_found")
    if target_listing.owner_id == user.id:
        raise ValidationAppError("Нельзя оценивать собственное объявление", code="own_listing")
    if await _blocked_between(db, user.id, target_listing.owner_id):
        raise ForbiddenError("Действие недоступно", code="blocked")

    existing_request = await db.scalar(
        select(Swipe).where(Swipe.user_id == user.id, Swipe.request_id == request_id)
    )
    if existing_request is not None:
        quota = await quota_service.get_quota(db, user.id)
        match = await _find_match_for_swipe(db, user.id, target_animal.id)
        conversation = await db.get(Conversation, match.conversation_id) if match else None
        return SwipeResponse(
            action=SwipeAction(existing_request.action),
            remaining=quota.remaining,
            limit=quota.limit,
            resets_at=quota.resets_at,
            unlimited=quota.unlimited,
            match_created=match is not None,
            conversation_public_id=conversation.public_id if conversation else None,
        )

    existing_swipe = await db.scalar(
        select(Swipe).where(
            Swipe.user_id == user.id,
            Swipe.target_kind == "listing",
            Swipe.target_id == target_listing.id,
        )
    )
    if existing_swipe is not None:
        if existing_swipe.action != action.value:
            raise ConflictError("Решение уже принято", code="swipe_exists")
        quota = await quota_service.get_quota(db, user.id)
        match = await _find_match_for_swipe(db, user.id, target_animal.id)
        conversation = await db.get(Conversation, match.conversation_id) if match else None
        return SwipeResponse(
            action=action,
            remaining=quota.remaining,
            limit=quota.limit,
            resets_at=quota.resets_at,
            unlimited=quota.unlimited,
            match_created=match is not None,
            conversation_public_id=conversation.public_id if conversation else None,
        )

    swipe_id = uuid4()
    record = Swipe(
        id=swipe_id,
        user_id=user.id,
        target_kind="listing",
        target_id=target_listing.id,
        animal_id=target_animal.id,
        action=action.value,
        source=source.value,
        request_id=request_id,
        consumed_quota=True,
    )
    db.add(record)
    try:
        # The swipe row must exist before quota_events references it, and the whole
        # unit of work (swipe + quota increment + match) commits or rolls back together.
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise ConflictError(
            "Не удалось сохранить действие, обновите ленту", code="swipe_conflict"
        ) from None

    quota = await quota_service.consume_quota(db, user.id, swipe_id=swipe_id)
    match: Match | None = None
    conversation: Conversation | None = None
    if action == SwipeAction.LIKE and listing_service.is_mating_purpose(target_listing.purpose):
        reciprocal = await _reciprocal_like(db, target_listing.owner_id, target_animal, user.id)
        if reciprocal is not None:
            partner_animal, partner_listing = reciprocal
            if not await _blocked_between(db, user.id, partner_animal.owner_id):
                match, conversation = await _create_match_and_conversation(
                    db,
                    target_listing=target_listing,
                    target_animal=target_animal,
                    user=user,
                    partner_animal=partner_animal,
                    partner_listing=partner_listing,
                )

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ConflictError(
            "Не удалось сохранить действие, обновите ленту", code="swipe_conflict"
        ) from None
    SWIPES.labels(action=action.value, source=source.value).inc()
    return SwipeResponse(
        action=action,
        remaining=quota.remaining,
        limit=quota.limit,
        resets_at=quota.resets_at,
        unlimited=quota.unlimited,
        match_created=match is not None,
        conversation_public_id=conversation.public_id if conversation else None,
    )


async def undo_last_swipe(db: AsyncSession, user: User) -> quota_service.QuotaStatus:
    entitlements = await get_entitlements(db, user.id)
    if Entitlement.UNDO not in entitlements:
        raise ForbiddenError("Отмена доступна по подписке", code="entitlement_required")
    last = await db.scalar(
        select(Swipe)
        .where(Swipe.user_id == user.id, Swipe.target_kind == "listing")
        .order_by(Swipe.created_at.desc())
        .limit(1)
    )
    if last is None:
        raise NotFoundError("Нечего отменять", code="nothing_to_undo")
    if last.animal_id is not None:
        match = await _find_match_for_swipe(db, user.id, last.animal_id)
        if match is not None:
            raise ConflictError(
                "Нельзя отменить действие: по нему уже создано совпадение", code="match_exists"
            )
    if last.consumed_quota:
        await quota_service.restore_quota(db, user.id)
    await db.delete(last)
    await db.commit()
    return await quota_service.get_quota(db, user.id)


async def add_favorite(db: AsyncSession, user: User, listing_public_id: UUID) -> None:
    listing = await db.scalar(select(Listing).where(Listing.public_id == listing_public_id))
    if listing is None or listing.status != listing_service.PUBLISHED:
        raise NotFoundError("Объявление не найдено", code="listing_not_found")
    stmt = (
        pg_insert(Favorite)
        .values(id=uuid4(), user_id=user.id, listing_id=listing.id)
        .on_conflict_do_nothing(index_elements=[Favorite.user_id, Favorite.listing_id])
    )
    await db.execute(stmt)
    await db.commit()


async def remove_favorite(db: AsyncSession, user: User, listing_public_id: UUID) -> None:
    listing = await db.scalar(select(Listing).where(Listing.public_id == listing_public_id))
    if listing is None:
        raise NotFoundError("Объявление не найдено", code="listing_not_found")
    await db.execute(
        delete(Favorite).where(Favorite.user_id == user.id, Favorite.listing_id == listing.id)
    )
    await db.commit()


async def list_favorites(db: AsyncSession, user: User) -> list[tuple[Listing, Animal]]:
    rows = (
        await db.execute(
            select(Listing, Animal)
            .join(Animal, Animal.id == Listing.animal_id)
            .join(Favorite, Favorite.listing_id == Listing.id)
            .where(Favorite.user_id == user.id)
            .order_by(Favorite.created_at.desc())
        )
    ).all()
    return [(row[0], row[1]) for row in rows]
