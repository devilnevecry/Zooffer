from __future__ import annotations

import hashlib
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import or_, select

from zooffer.api.cookies import clear_session_cookie
from zooffer.api.deps import CurrentAuth, DbSession, OptionalAuth, request_ip_hash
from zooffer.core.errors import NotFoundError, ValidationAppError
from zooffer.core.rate_limit import limiter
from zooffer.core.security import encrypt_value, generate_token
from zooffer.core.utils import utcnow
from zooffer.db.models import (
    Animal,
    AnimalPhoto,
    Listing,
    Match,
    NotificationPreference,
    Partner,
    PartnerClick,
    PartnerInquiry,
    PartnerOffer,
    Plan,
    Profile,
)
from zooffer.schemas.account import (
    AccountDeleteRequest,
    BlockedUserList,
    BlockedUserView,
    MatchListView,
    MatchView,
    NotificationPreferenceList,
    NotificationPreferenceUpdateRequest,
    NotificationPreferenceView,
    PartnerInquiryRequest,
    PartnerOfferList,
    PartnerOfferView,
    PlanList,
    PlanView,
    SubscriptionView,
    SupportTicketCreateRequest,
    SupportTicketView,
)
from zooffer.schemas.auth import OkResponse
from zooffer.services import account_service, billing_service
from zooffer.services.listing_service import display_name
from zooffer.services.media import media_url, thumb_key_for

router = APIRouter(tags=["account"])
public_router = APIRouter(prefix="/public", tags=["public"])
click_router = APIRouter(tags=["partners"])

DEFAULT_CATEGORIES = (
    "matches",
    "messages",
    "inquiries",
    "listing_moderation",
    "subscriptions",
    "partners",
    "support",
    "security",
)


@router.get("/matches", response_model=MatchListView)
async def list_matches(auth: CurrentAuth, db: DbSession) -> MatchListView:
    rows = (
        await db.scalars(
            select(Match)
            .where(or_(Match.owner_a_id == auth.user.id, Match.owner_b_id == auth.user.id))
            .order_by(Match.created_at.desc())
        )
    ).all()
    items: list[MatchView] = []
    for match in rows:
        partner_animal_id = (
            match.animal_b_id if match.owner_a_id == auth.user.id else match.animal_a_id
        )
        animal = await db.get(Animal, partner_animal_id)
        if animal is None:
            continue
        listing = await db.scalar(
            select(Listing)
            .where(
                Listing.animal_id == animal.id,
                Listing.status == "published",
            )
            .order_by(Listing.published_at.desc())
            .limit(1)
        )
        photo = await db.scalar(
            select(AnimalPhoto)
            .where(AnimalPhoto.animal_id == animal.id)
            .order_by(AnimalPhoto.is_primary.desc(), AnimalPhoto.position.asc())
            .limit(1)
        )
        profile = await db.get(Profile, animal.owner_id)
        conversation_public_id = None
        if match.conversation_id is not None:
            from zooffer.db.models import Conversation

            conversation_public_id = await db.scalar(
                select(Conversation.public_id).where(Conversation.id == match.conversation_id)
            )
        items.append(
            MatchView(
                conversation_public_id=conversation_public_id,
                animal_name=animal.name,
                animal_public_id=animal.public_id,
                listing_slug=listing.slug if listing else None,
                listing_title=listing.title if listing else None,
                species=animal.species,
                breed=animal.breed_text,
                sex=animal.sex,
                primary_photo_url=(
                    media_url(thumb_key_for(photo.storage_key)) if photo is not None else None
                ),
                owner_display_name=display_name(profile),
                created_at=match.created_at,
            )
        )
    return MatchListView(items=items)


@router.get("/notification-preferences", response_model=NotificationPreferenceList)
async def get_notification_preferences(
    auth: CurrentAuth, db: DbSession
) -> NotificationPreferenceList:
    stored = {
        row.category: row
        for row in (
            await db.scalars(
                select(NotificationPreference).where(
                    NotificationPreference.user_id == auth.user.id
                )
            )
        ).all()
    }
    items = []
    for category in DEFAULT_CATEGORIES:
        row = stored.get(category)
        items.append(
            NotificationPreferenceView(
                category=category,
                in_app=row.in_app if row else True,
                telegram=row.telegram if row else category != "partners",
                email=row.email if row else False,
                quiet_from=row.quiet_from if row else None,
                quiet_to=row.quiet_to if row else None,
            )
        )
    return NotificationPreferenceList(items=items)


@router.put("/notification-preferences", response_model=NotificationPreferenceList)
async def update_notification_preferences(
    payload: NotificationPreferenceUpdateRequest, auth: CurrentAuth, db: DbSession
) -> NotificationPreferenceList:
    for item in payload.items:
        row = await db.get(NotificationPreference, (auth.user.id, item.category))
        if row is None:
            row = NotificationPreference(user_id=auth.user.id, category=item.category)
            db.add(row)
        row.in_app = item.in_app
        row.telegram = item.telegram
        row.email = item.email
        row.quiet_from = item.quiet_from
        row.quiet_to = item.quiet_to
    await db.commit()
    return await get_notification_preferences(auth, db)


@router.post("/support/tickets", response_model=SupportTicketView, status_code=201)
async def create_support_ticket(
    payload: SupportTicketCreateRequest, auth: CurrentAuth, db: DbSession
) -> SupportTicketView:
    await limiter.hit(f"support:{auth.user.id}", limit=5, window_seconds=3600)
    ticket = await account_service.create_support_ticket(
        db,
        auth.user,
        subject=payload.subject,
        message=payload.message,
        channel="web",
    )
    return SupportTicketView(
        public_id=ticket.public_id,
        subject=ticket.subject,
        status=ticket.status,
        created_at=ticket.created_at,
    )


@public_router.get("/partners", response_model=PartnerOfferList)
async def list_partner_offers(db: DbSession) -> PartnerOfferList:
    now = utcnow()
    rows = (
        await db.execute(
            select(PartnerOffer, Partner)
            .join(Partner, Partner.id == PartnerOffer.partner_id)
            .where(
                Partner.status == "active",
                PartnerOffer.status == "active",
                or_(PartnerOffer.starts_at.is_(None), PartnerOffer.starts_at <= now),
                or_(PartnerOffer.ends_at.is_(None), PartnerOffer.ends_at > now),
            )
            .order_by(PartnerOffer.is_featured.desc(), PartnerOffer.sort_order, PartnerOffer.title)
        )
    ).all()
    return PartnerOfferList(
        items=[
            PartnerOfferView(
                public_id=offer.id,
                partner_name=partner.name,
                partner_slug=partner.slug,
                title=offer.title,
                description=offer.description,
                category=offer.category,
                discount_code=offer.discount_code,
                terms=offer.terms,
                destination_url=offer.destination_url,
                is_featured=offer.is_featured,
                erid=offer.erid,
                ad_label=offer.ad_label,
            )
            for offer, partner in rows
        ]
    )


@public_router.post("/partner-inquiries", status_code=201)
async def create_partner_inquiry(payload: PartnerInquiryRequest, db: DbSession) -> dict[str, bool]:
    await limiter.hit(
        f"partner-inquiry:{payload.email.strip().lower()}", limit=3, window_seconds=86_400
    )
    now = utcnow()
    db.add(
        PartnerInquiry(
            id=uuid4(),
            company=payload.company,
            contact_name=payload.contact_name,
            email_encrypted=encrypt_value(payload.email.strip().lower()),
            phone_encrypted=encrypt_value(payload.phone) if payload.phone else None,
            category=payload.category,
            message=payload.message,
            consent_at=now,
            status="new",
        )
    )
    await db.commit()
    return {"ok": True}


@public_router.get("/plans", response_model=PlanList)
async def list_plans(db: DbSession) -> PlanList:
    plans = (
        await db.scalars(
            select(Plan)
            .where(Plan.is_active.is_(True))
            .order_by(Plan.sort_order, Plan.price_kopecks)
        )
    ).all()
    return PlanList(
        items=[
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
    )


@router.get("/billing/subscription", response_model=SubscriptionView)
async def get_subscription(auth: CurrentAuth, db: DbSession) -> SubscriptionView:
    return await billing_service.subscription_view(db, auth.user)


@router.post("/billing/cancel", response_model=SubscriptionView)
async def cancel_subscription(auth: CurrentAuth, db: DbSession) -> SubscriptionView:
    return await billing_service.cancel_subscription(db, auth.user)


@router.get("/account/export")
async def export_account(
    auth: CurrentAuth, db: DbSession, response: Response
) -> dict[str, Any]:
    await limiter.hit(f"export:{auth.user.id}", limit=3, window_seconds=3600)
    archive = await account_service.export_user_data(db, auth.user)
    response.headers["Content-Disposition"] = (
        f'attachment; filename="zooffer-account-{auth.user.public_id}.json"'
    )
    return archive


@router.delete("/account", response_model=OkResponse)
async def delete_account(
    payload: AccountDeleteRequest,
    auth: CurrentAuth,
    db: DbSession,
    response: Response,
) -> OkResponse:
    await limiter.hit(f"delete-account:{auth.user.id}", limit=3, window_seconds=3600)
    await account_service.delete_account(db, auth.user, payload.confirmation)
    clear_session_cookie(response)
    return OkResponse()


@router.get("/blocked-users", response_model=BlockedUserList)
async def list_blocked_users(auth: CurrentAuth, db: DbSession) -> BlockedUserList:
    rows = await account_service.list_blocked(db, auth.user.id)
    return BlockedUserList(
        items=[
            BlockedUserView(
                id=UUID(row["id"]),
                display_name=row["display_name"],
                blocked_at=row["blocked_at"],
            )
            for row in rows
        ]
    )


@router.delete("/blocked-users/{block_id}", response_model=OkResponse)
async def unblock_user(
    block_id: UUID, auth: CurrentAuth, db: DbSession
) -> OkResponse:
    await account_service.unblock(db, auth.user.id, block_id)
    return OkResponse()


@click_router.get("/go/{offer_id}")
async def track_partner_click(
    offer_id: UUID,
    request: Request,
    db: DbSession,
    auth: OptionalAuth,
) -> RedirectResponse:
    now = utcnow()
    row = (
        await db.execute(
            select(PartnerOffer, Partner)
            .join(Partner, Partner.id == PartnerOffer.partner_id)
            .where(
                PartnerOffer.id == offer_id,
                PartnerOffer.status == "active",
                Partner.status == "active",
                or_(PartnerOffer.starts_at.is_(None), PartnerOffer.starts_at <= now),
                or_(PartnerOffer.ends_at.is_(None), PartnerOffer.ends_at > now),
            )
        )
    ).first()
    if row is None:
        raise NotFoundError("Предложение не найдено", code="partner_offer_not_found")
    offer, _partner = row
    if not offer.destination_url.startswith(("https://", "http://")):
        raise ValidationAppError("Некорректная ссылка предложения", code="invalid_destination")
    await limiter.hit(f"partner-click:{offer_id}", limit=120, window_seconds=60)
    user_agent = request.headers.get("user-agent") or ""
    db.add(
        PartnerClick(
            id=uuid4(),
            offer_id=offer.id,
            user_id=auth.user.id if auth else None,
            ip_hash=request_ip_hash(request),
            ua_hash=(
                hashlib.sha256(user_agent.encode()).hexdigest() if user_agent else None
            ),
            attribution_token=generate_token(),
        )
    )
    await db.commit()
    return RedirectResponse(offer.destination_url, status_code=302)
