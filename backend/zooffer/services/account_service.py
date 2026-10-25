from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from zooffer.core.enums import ListingStatus, UserStatus
from zooffer.core.errors import ValidationAppError
from zooffer.core.utils import utcnow
from zooffer.db.models import (
    Animal,
    AnimalDocument,
    AnimalPhoto,
    AuditLog,
    AuthIdentity,
    Block,
    Consent,
    Conversation,
    ConversationParticipant,
    Credential,
    Favorite,
    Listing,
    Match,
    Message,
    Notification,
    Profile,
    Subscription,
    SupportMessage,
    SupportTicket,
    TelegramChat,
    User,
    UserPrivateData,
)
from zooffer.services import auth_service
from zooffer.services.listing_service import display_name
from zooffer.services.media import media_url, thumb_key_for


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


async def export_user_data(db: AsyncSession, user: User) -> dict[str, Any]:
    """Return a portable JSON archive of the authenticated user's own data.

    Other users appear only through the same public display name used everywhere
    else; no contact details, Telegram identifiers, or internal IDs are included.
    """
    profile = await db.get(Profile, user.id)
    private = await db.get(UserPrivateData, user.id)
    animals = list(
        (
            await db.scalars(
                select(Animal).where(Animal.owner_id == user.id).order_by(Animal.created_at)
            )
        ).all()
    )
    animal_ids = [animal.id for animal in animals]
    photos: dict[UUID, list[AnimalPhoto]] = {}
    documents: dict[UUID, list[AnimalDocument]] = {}
    if animal_ids:
        for photo in (
            await db.scalars(
                select(AnimalPhoto)
                .where(AnimalPhoto.animal_id.in_(animal_ids))
                .order_by(AnimalPhoto.position)
            )
        ).all():
            photos.setdefault(photo.animal_id, []).append(photo)
        for document in (
            await db.scalars(select(AnimalDocument).where(AnimalDocument.animal_id.in_(animal_ids)))
        ).all():
            documents.setdefault(document.animal_id, []).append(document)

    listings = list(
        (
            await db.scalars(
                select(Listing).where(Listing.owner_id == user.id).order_by(Listing.created_at)
            )
        ).all()
    )
    favorites = list((await db.scalars(select(Favorite).where(Favorite.user_id == user.id))).all())
    favorite_listings = []
    for favorite in favorites:
        listing = await db.get(Listing, favorite.listing_id)
        if listing is None:
            continue
        favorite_listings.append(
            {
                "listing_public_id": str(listing.public_id),
                "slug": listing.slug,
                "title": listing.title,
                "status": listing.status,
                "saved_at": _iso(favorite.created_at),
            }
        )

    matches = list(
        (
            await db.scalars(
                select(Match)
                .where(or_(Match.owner_a_id == user.id, Match.owner_b_id == user.id))
                .order_by(Match.created_at)
            )
        ).all()
    )
    match_items = []
    for match in matches:
        partner_animal_id = match.animal_b_id if match.owner_a_id == user.id else match.animal_a_id
        partner_animal = await db.get(Animal, partner_animal_id)
        if partner_animal is None:
            continue
        partner_profile = await db.get(Profile, partner_animal.owner_id)
        match_items.append(
            {
                "animal_name": partner_animal.name,
                "animal_public_id": str(partner_animal.public_id),
                "owner_display_name": display_name(partner_profile),
                "matched_at": _iso(match.created_at),
            }
        )

    conversation_ids = list(
        (
            await db.scalars(
                select(ConversationParticipant.conversation_id).where(
                    ConversationParticipant.user_id == user.id
                )
            )
        ).all()
    )
    conversations = []
    for conversation_id in conversation_ids:
        conversation = await db.get(Conversation, conversation_id)
        if conversation is None:
            continue
        other_id = await db.scalar(
            select(ConversationParticipant.user_id).where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id != user.id,
            )
        )
        other_profile = await db.get(Profile, other_id) if other_id else None
        messages = (
            await db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
            )
        ).all()
        conversations.append(
            {
                "conversation_public_id": str(conversation.public_id),
                "type": conversation.conversation_type,
                "counterpart_display_name": display_name(other_profile),
                "messages": [
                    {
                        "body": message.body,
                        "mine": message.sender_id == user.id,
                        "created_at": _iso(message.created_at),
                        "edited_at": _iso(message.edited_at),
                        "deleted": message.deleted_at is not None,
                    }
                    for message in messages
                ],
            }
        )

    notifications = list(
        (
            await db.scalars(
                select(Notification)
                .where(Notification.user_id == user.id)
                .order_by(Notification.created_at)
            )
        ).all()
    )
    consents = list((await db.scalars(select(Consent).where(Consent.user_id == user.id))).all())

    return {
        "format": "zooffer-account-export",
        "version": 1,
        "generated_at": _iso(utcnow()),
        "account": {
            "public_id": str(user.public_id),
            "status": user.status,
            "locale": user.locale,
            "timezone": user.timezone,
            "created_at": _iso(user.created_at),
            "email_verified_at": _iso(user.email_verified_at),
        },
        "profile": {
            "first_name": profile.public_first_name if profile else None,
            "last_name": profile.public_last_name if profile else None,
            "city_id": profile.city_id if profile else None,
            "region_id": profile.region_id if profile else None,
        },
        # The ORM's EncryptedText type has already decrypted these fields for this
        # owner-scoped export; the archive is returned only to the authenticated user.
        "private_data": {
            "email": private.email_encrypted if private else None,
            "phone": private.phone_encrypted if private else None,
            "date_of_birth": private.date_of_birth_encrypted if private else None,
            "address": private.address_encrypted if private else None,
            "telegram_username": private.telegram_username_encrypted if private else None,
        },
        "animals": [
            {
                "public_id": str(animal.public_id),
                "name": animal.name,
                "species": animal.species,
                "breed": animal.breed_text,
                "sex": animal.sex,
                "birth_date": animal.birth_date.isoformat() if animal.birth_date else None,
                "colour": animal.colour,
                "size": animal.size,
                "has_pedigree": animal.has_pedigree,
                "pedigree_registry": animal.pedigree_registry,
                "pedigree_number": animal.pedigree_number,
                "vaccinated": animal.vaccinated,
                "health_notes": animal.health_notes,
                "description": animal.description,
                "created_at": _iso(animal.created_at),
                "photos": [
                    {
                        "url": media_url(photo.storage_key),
                        "thumb_url": media_url(thumb_key_for(photo.storage_key)),
                        "is_primary": photo.is_primary,
                        "width": photo.width,
                        "height": photo.height,
                        "created_at": _iso(photo.created_at),
                    }
                    for photo in photos.get(animal.id, [])
                ],
                "documents": [
                    {
                        "document_type": document.document_type,
                        "content_type": document.content_type,
                        "status": document.status,
                        "created_at": _iso(document.created_at),
                    }
                    for document in documents.get(animal.id, [])
                ],
            }
            for animal in animals
        ],
        "listings": [
            {
                "public_id": str(listing.public_id),
                "slug": listing.slug,
                "title": listing.title,
                "description": listing.description,
                "purpose": listing.purpose,
                "status": listing.status,
                "price_kopecks": listing.price_kopecks,
                "currency": listing.currency,
                "negotiable": listing.negotiable,
                "city_id": listing.city_id,
                "region_id": listing.region_id,
                "created_at": _iso(listing.created_at),
                "published_at": _iso(listing.published_at),
                "expires_at": _iso(listing.expires_at),
            }
            for listing in listings
        ],
        "favorites": favorite_listings,
        "matches": match_items,
        "conversations": conversations,
        "notifications": [
            {
                "category": item.category,
                "title": item.title,
                "body": item.body,
                "read_at": _iso(item.read_at),
                "created_at": _iso(item.created_at),
            }
            for item in notifications
        ],
        "consents": [
            {
                "document": consent.document,
                "version": consent.version,
                "channel": consent.channel,
                "granted_at": _iso(consent.granted_at),
            }
            for consent in consents
        ],
    }


async def delete_account(db: AsyncSession, user: User, confirmation: str) -> None:
    """Irreversibly deactivate the account and minimise retained personal data.

    Legal/financial records are not fabricated or removed here; payment events are
    retained by the provider and described in the privacy policy. We keep an
    append-only audit record with no personal payload.
    """
    if confirmation.strip().upper() != "УДАЛИТЬ":
        raise ValidationAppError(
            "Введите слово УДАЛИТЬ, чтобы подтвердить удаление аккаунта",
            code="confirmation_failed",
        )
    now = utcnow()

    await auth_service.revoke_all_sessions(db, user.id, "account_deleted")

    profile = await db.get(Profile, user.id)
    if profile:
        profile.public_first_name = None
        profile.public_last_name = None
        profile.city_id = None
        profile.region_id = None

    private = await db.get(UserPrivateData, user.id)
    if private:
        private.email_encrypted = None
        private.email_hash = None
        private.phone_encrypted = None
        private.date_of_birth_encrypted = None
        private.address_encrypted = None
        private.telegram_username_encrypted = None

    await db.execute(delete(Credential).where(Credential.user_id == user.id))
    await db.execute(delete(AuthIdentity).where(AuthIdentity.user_id == user.id))
    await db.execute(delete(TelegramChat).where(TelegramChat.user_id == user.id))
    await db.execute(
        delete(Block).where(or_(Block.blocker_id == user.id, Block.blocked_id == user.id))
    )

    for listing in (await db.scalars(select(Listing).where(Listing.owner_id == user.id))).all():
        listing.status = ListingStatus.ARCHIVED.value
        listing.archived_at = now
    for animal in (await db.scalars(select(Animal).where(Animal.owner_id == user.id))).all():
        animal.archived_at = now
    for subscription in (
        await db.scalars(
            select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.status.in_(["pending", "active", "past_due"]),
            )
        )
    ).all():
        subscription.status = "canceled"
        subscription.canceled_at = now
        subscription.cancel_at_period_end = True

    user.status = UserStatus.DELETED.value
    user.deleted_at = now
    db.add(
        AuditLog(
            actor_id=None,
            actor_role=user.role,
            action="account.deleted",
            object_type="user",
            object_id=str(user.public_id),
        )
    )
    await db.commit()


async def list_blocked(db: AsyncSession, user_id: UUID) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(Block, Profile)
            .outerjoin(Profile, Profile.user_id == Block.blocked_id)
            .where(Block.blocker_id == user_id)
            .order_by(Block.created_at.desc())
        )
    ).all()
    return [
        {
            "id": str(block.id),
            "display_name": display_name(profile),
            "blocked_at": _iso(block.created_at),
        }
        for block, profile in rows
    ]


async def unblock(db: AsyncSession, user_id: UUID, block_id: UUID) -> None:
    block = await db.get(Block, block_id)
    if block is None or block.blocker_id != user_id:
        raise ValidationAppError("Блокировка не найдена", code="block_not_found")
    await db.delete(block)
    await db.commit()


async def create_support_ticket(
    db: AsyncSession,
    user: User,
    *,
    subject: str,
    message: str,
    channel: str = "web",
) -> SupportTicket:
    """Create a support ticket with an initial user message for any channel."""
    ticket = SupportTicket(
        id=uuid4(),
        user_id=user.id,
        public_id=uuid4(),
        subject=subject.strip(),
        status="open",
        channel=channel,
    )
    db.add(ticket)
    await db.flush()
    db.add(
        SupportMessage(
            id=uuid4(),
            ticket_id=ticket.id,
            sender_id=user.id,
            is_staff=False,
            body=message.strip(),
        )
    )
    await db.commit()
    await db.refresh(ticket)
    return ticket
