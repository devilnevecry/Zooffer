from __future__ import annotations

import json
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from zooffer.core.enums import ListingStatus
from zooffer.core.errors import NotFoundError, ValidationAppError
from zooffer.core.utils import utcnow
from zooffer.db.models import (
    Animal,
    AnimalPhoto,
    AuditLog,
    City,
    Listing,
    Match,
    ModerationAction,
    PaymentOrder,
    Plan,
    Profile,
    Report,
    Subscription,
    SupportMessage,
    SupportTicket,
    Swipe,
    SystemSetting,
    User,
    UserPrivateData,
)
from zooffer.schemas.admin import (
    AdminAuditView,
    AdminDashboardView,
    AdminListingView,
    AdminPaymentView,
    AdminRecentItem,
    AdminReportView,
    AdminSettingView,
    AdminStatsView,
    AdminSupportTicketView,
    AdminUserView,
)
from zooffer.services import notification_service
from zooffer.services.listing_service import display_name
from zooffer.services.media import media_url, thumb_key_for

SETTING_DEFAULTS: dict[str, Any] = {
    "free_daily_swipes": 20,
    "support_email": "support@zooffer.ru",
    "enable_telegram": False,
    "enable_glass": True,
}


async def _audit(
    db: AsyncSession,
    *,
    actor: User,
    action: str,
    object_type: str,
    object_id: str | None,
    metadata: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            id=uuid4(),
            actor_id=actor.id,
            actor_role=actor.role,
            action=action,
            object_type=object_type,
            object_id=object_id,
            metadata_json=metadata,
        )
    )


async def dashboard(db: AsyncSession) -> AdminDashboardView:
    now = utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    users_total = int(await db.scalar(select(func.count()).select_from(User)) or 0)
    users_new_week = int(
        await db.scalar(select(func.count()).select_from(User).where(User.created_at >= week_ago))
        or 0
    )
    listings_published = int(
        await db.scalar(
            select(func.count())
            .select_from(Listing)
            .where(Listing.status == ListingStatus.PUBLISHED.value, Listing.deleted_at.is_(None))
        )
        or 0
    )
    listings_pending = int(
        await db.scalar(
            select(func.count())
            .select_from(Listing)
            .where(Listing.status == ListingStatus.PENDING_MODERATION.value)
        )
        or 0
    )
    reports_open = int(
        await db.scalar(
            select(func.count()).select_from(Report).where(Report.status == "open")
        )
        or 0
    )
    support_open = int(
        await db.scalar(
            select(func.count())
            .select_from(SupportTicket)
            .where(SupportTicket.status.in_(["open", "pending"]))
        )
        or 0
    )
    subscriptions_active = int(
        await db.scalar(
            select(func.count())
            .select_from(Subscription)
            .where(
                Subscription.status == "active",
                Subscription.current_period_end > now,
            )
        )
        or 0
    )
    revenue = int(
        await db.scalar(
            select(func.coalesce(func.sum(PaymentOrder.amount_kopecks), 0)).where(
                PaymentOrder.status == "paid", PaymentOrder.paid_at >= month_ago
            )
        )
        or 0
    )
    swipes_today = int(
        await db.scalar(
            select(func.count())
            .select_from(Swipe)
            .where(
                Swipe.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0)
            )
        )
        or 0
    )
    matches_total = int(
        await db.scalar(select(func.count()).select_from(Match)) or 0
    )
    rows = (
        await db.scalars(
            select(AuditLog).order_by(AuditLog.created_at.desc()).limit(10)
        )
    ).all()
    recent = [
        AdminRecentItem(
            created_at=row.created_at,
            action=row.action,
            object_type=row.object_type,
            object_id=row.object_id,
            actor_role=row.actor_role,
        )
        for row in rows
    ]
    return AdminDashboardView(
        stats=AdminStatsView(
            users_total=users_total,
            users_new_week=users_new_week,
            listings_published=listings_published,
            listings_pending=listings_pending,
            reports_open=reports_open,
            support_open=support_open,
            subscriptions_active=subscriptions_active,
            revenue_kopecks_30d=revenue,
            swipes_today=swipes_today,
            matches_total=matches_total,
        ),
        recent_actions=recent,
    )


async def list_listings(
    db: AsyncSession, *, status: str | None = None, query: str | None = None, limit: int = 100
) -> tuple[list[AdminListingView], int]:
    stmt = (
        select(Listing, Animal, Profile, City, User)
        .join(Animal, Animal.id == Listing.animal_id)
        .join(User, User.id == Listing.owner_id)
        .outerjoin(Profile, Profile.user_id == Listing.owner_id)
        .outerjoin(City, City.id == Listing.city_id)
    )
    if status:
        stmt = stmt.where(Listing.status == status)
    if query:
        cleaned = query.strip()[:120]
        if cleaned:
            stmt = stmt.where(
                or_(Listing.title.ilike(f"%{cleaned}%"), Animal.name.ilike(f"%{cleaned}%"))
            )
    total = int(
        await db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    )
    rows = (await db.execute(stmt.order_by(Listing.created_at.desc()).limit(limit))).all()
    animal_ids = [row[1].id for row in rows]
    photos = {}
    if animal_ids:
        photo_rows = (
            await db.scalars(
                select(AnimalPhoto)
                .where(AnimalPhoto.animal_id.in_(animal_ids))
                .order_by(AnimalPhoto.is_primary.desc(), AnimalPhoto.position.asc())
            )
        ).all()
        for photo in photo_rows:
            photos.setdefault(photo.animal_id, photo)
    items = [
        AdminListingView(
            public_id=listing.public_id,
            slug=listing.slug,
            title=listing.title,
            purpose=listing.purpose,
            status=listing.status,
            price_kopecks=listing.price_kopecks,
            owner_name=display_name(profile),
            owner_public_id=user.public_id,
            animal_name=animal.name,
            species=animal.species,
            city_name=city.name if city else None,
            photo_url=(
                media_url(thumb_key_for(photos[animal.id].storage_key))
                if animal.id in photos
                else None
            ),
            moderation_reason=listing.moderation_reason,
            quality_score=listing.quality_score,
            created_at=listing.created_at,
            published_at=listing.published_at,
        )
        for listing, animal, profile, city, user in rows
    ]
    return items, total


async def moderate_listing(
    db: AsyncSession, actor: User, public_id: UUID, *, action: str, reason: str
) -> AdminListingView:
    row = (
        await db.execute(
            select(Listing, Animal, Profile, City, User)
            .join(Animal, Animal.id == Listing.animal_id)
            .join(User, User.id == Listing.owner_id)
            .outerjoin(Profile, Profile.user_id == Listing.owner_id)
            .outerjoin(City, City.id == Listing.city_id)
            .where(Listing.public_id == public_id)
        )
    ).first()
    if row is None:
        raise NotFoundError("Объявление не найдено", code="listing_not_found")
    listing, animal, profile, city, user = row
    if action == "approve":
        if animal.archived_at is not None:
            raise ValidationAppError(
                "Нельзя опубликовать архивное животное", code="animal_archived"
            )
        photo = await db.scalar(
            select(AnimalPhoto.id).where(AnimalPhoto.animal_id == animal.id).limit(1)
        )
        if photo is None:
            raise ValidationAppError(
                "Нельзя опубликовать объявление без фото", code="photo_required"
            )
        listing.status = ListingStatus.PUBLISHED.value
        listing.published_at = utcnow()
        listing.expires_at = utcnow() + timedelta(days=60)
        listing.moderation_reason = None
    else:
        listing.status = ListingStatus.REJECTED.value
        listing.moderation_reason = reason
    listing.moderated_at = utcnow()
    db.add(
        ModerationAction(
            id=uuid4(),
            moderator_id=actor.id,
            target_type="listing",
            target_public_id=str(listing.public_id),
            action=action,
            reason=reason,
        )
    )
    await _audit(
        db,
        actor=actor,
        action=f"listing.{action}",
        object_type="listing",
        object_id=str(listing.public_id),
        metadata={"reason": reason},
    )
    notification_service.listing_moderated(
        db,
        owner_id=listing.owner_id,
        listing_slug=listing.slug,
        listing_public_id=listing.public_id,
        approved=action == "approve",
        reason=reason,
    )
    await db.commit()
    photo = await db.scalar(
        select(AnimalPhoto)
        .where(AnimalPhoto.animal_id == animal.id)
        .order_by(AnimalPhoto.is_primary.desc(), AnimalPhoto.position.asc())
        .limit(1)
    )
    return AdminListingView(
        public_id=listing.public_id,
        slug=listing.slug,
        title=listing.title,
        purpose=listing.purpose,
        status=listing.status,
        price_kopecks=listing.price_kopecks,
        owner_name=display_name(profile),
        owner_public_id=user.public_id,
        animal_name=animal.name,
        species=animal.species,
        city_name=city.name if city else None,
        photo_url=media_url(thumb_key_for(photo.storage_key)) if photo else None,
        moderation_reason=listing.moderation_reason,
        quality_score=listing.quality_score,
        created_at=listing.created_at,
        published_at=listing.published_at,
    )


async def list_reports(db: AsyncSession, *, status: str | None = None) -> list[AdminReportView]:
    stmt = select(Report, Profile).outerjoin(Profile, Profile.user_id == Report.reporter_id)
    if status:
        stmt = stmt.where(Report.status == status)
    rows = (await db.execute(stmt.order_by(Report.created_at.desc()).limit(200))).all()
    return [
        AdminReportView(
            id=report.id,
            target_type=report.target_type,
            target_public_id=report.target_public_id,
            reason=report.reason,
            details=report.details,
            status=report.status,
            reporter_name=display_name(profile),
            created_at=report.created_at,
            resolved_at=report.resolved_at,
        )
        for report, profile in rows
    ]


async def resolve_report(
    db: AsyncSession, actor: User, report_id: UUID, *, status: str, resolution: str
) -> AdminReportView:
    report = await db.get(Report, report_id)
    if report is None:
        raise NotFoundError("Жалоба не найдена", code="report_not_found")
    report.status = status
    report.resolution = resolution
    report.resolved_at = utcnow() if status in {"resolved", "dismissed"} else None
    await _audit(
        db,
        actor=actor,
        action=f"report.{status}",
        object_type="report",
        object_id=str(report.id),
        metadata={"resolution": resolution},
    )
    await db.commit()
    profile = await db.get(Profile, report.reporter_id) if report.reporter_id else None
    return AdminReportView(
        id=report.id,
        target_type=report.target_type,
        target_public_id=report.target_public_id,
        reason=report.reason,
        details=report.details,
        status=report.status,
        reporter_name=display_name(profile),
        created_at=report.created_at,
        resolved_at=report.resolved_at,
    )


async def list_users(
    db: AsyncSession, *, query: str | None = None, limit: int = 100
) -> tuple[list[AdminUserView], int]:
    stmt = (
        select(User, Profile, City, UserPrivateData)
        .outerjoin(Profile, Profile.user_id == User.id)
        .outerjoin(City, City.id == Profile.city_id)
        .outerjoin(UserPrivateData, UserPrivateData.user_id == User.id)
    )
    if query:
        cleaned = query.strip()[:120]
        if cleaned:
            stmt = stmt.where(
                or_(
                    Profile.public_first_name.ilike(f"%{cleaned}%"),
                    Profile.public_last_name.ilike(f"%{cleaned}%"),
                    UserPrivateData.email_hash == cleaned,
                )
            )
    total = int(
        await db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    )
    rows = (await db.execute(stmt.order_by(User.created_at.desc()).limit(limit))).all()
    counts = dict(
        (
            await db.execute(
                select(Listing.owner_id, func.count())
                .where(Listing.owner_id.in_([row[0].id for row in rows]))
                .group_by(Listing.owner_id)
            )
        ).all()
    )
    return (
        [
            AdminUserView(
                public_id=user.public_id,
                display_name=display_name(profile),
                email=private.email_encrypted if private else None,
                role=user.role,
                status=user.status,
                city_name=city.name if city else None,
                listings_count=int(counts.get(user.id, 0)),
                created_at=user.created_at,
                mfa_enabled=user.mfa_enabled,
            )
            for user, profile, city, private in rows
        ],
        total,
    )


async def update_user(
    db: AsyncSession,
    actor: User,
    public_id: UUID,
    *,
    role: str | None,
    status: str | None,
) -> AdminUserView:
    user = await db.scalar(select(User).where(User.public_id == public_id))
    if user is None:
        raise NotFoundError("Пользователь не найден", code="user_not_found")
    if user.id == actor.id and role is not None and role != user.role:
        raise ValidationAppError("Нельзя изменить собственную роль", code="self_role_change")
    if role is not None:
        user.role = role
    if status is not None:
        user.status = status
    await _audit(
        db,
        actor=actor,
        action="user.update",
        object_type="user",
        object_id=str(user.public_id),
        metadata={"role": role, "status": status},
    )
    await db.commit()
    profile = await db.get(Profile, user.id)
    private = await db.get(UserPrivateData, user.id)
    return AdminUserView(
        public_id=user.public_id,
        display_name=display_name(profile),
        email=private.email_encrypted if private else None,
        role=user.role,
        status=user.status,
        city_name=None,
        listings_count=int(
            await db.scalar(
                select(func.count()).select_from(Listing).where(Listing.owner_id == user.id)
            )
            or 0
        ),
        created_at=user.created_at,
        mfa_enabled=user.mfa_enabled,
    )


async def list_support(db: AsyncSession) -> list[AdminSupportTicketView]:
    rows = (
        await db.execute(
            select(SupportTicket, Profile)
            .outerjoin(Profile, Profile.user_id == SupportTicket.user_id)
            .order_by(SupportTicket.updated_at.desc())
            .limit(200)
        )
    ).all()
    items = []
    for ticket, profile in rows:
        last = await db.scalar(
            select(SupportMessage.body)
            .where(SupportMessage.ticket_id == ticket.id)
            .order_by(SupportMessage.created_at.desc())
            .limit(1)
        )
        items.append(
            AdminSupportTicketView(
                public_id=ticket.public_id,
                subject=ticket.subject,
                status=ticket.status,
                channel=ticket.channel,
                user_name=display_name(profile),
                last_message=last,
                created_at=ticket.created_at,
                updated_at=ticket.updated_at,
            )
        )
    return items


async def reply_support(
    db: AsyncSession, actor: User, ticket_public_id: UUID, *, message: str, status: str
) -> AdminSupportTicketView:
    ticket = await db.scalar(
        select(SupportTicket).where(SupportTicket.public_id == ticket_public_id)
    )
    if ticket is None:
        raise NotFoundError("Обращение не найдено", code="ticket_not_found")
    db.add(
        SupportMessage(
            id=uuid4(),
            ticket_id=ticket.id,
            sender_id=actor.id,
            is_staff=True,
            body=message.strip(),
        )
    )
    ticket.status = status
    # `updated_at` uses a server-side onupdate, so it is expired after commit.
    # Set it explicitly to keep the response DTO usable without an extra query.
    ticket.updated_at = utcnow()
    if ticket.user_id is not None:
        notification_service.support_reply(
            db,
            user_id=ticket.user_id,
            ticket_public_id=ticket.public_id,
            subject=ticket.subject,
        )
    await _audit(
        db,
        actor=actor,
        action="support.reply",
        object_type="support_ticket",
        object_id=str(ticket.public_id),
    )
    await db.commit()
    profile = await db.get(Profile, ticket.user_id) if ticket.user_id else None
    return AdminSupportTicketView(
        public_id=ticket.public_id,
        subject=ticket.subject,
        status=ticket.status,
        channel=ticket.channel,
        user_name=display_name(profile),
        last_message=message.strip(),
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


async def get_settings(db: AsyncSession) -> list[AdminSettingView]:
    stored = {row.key: row for row in (await db.scalars(select(SystemSetting))).all()}
    items = []
    for key, default in SETTING_DEFAULTS.items():
        row = stored.get(key)
        value = row.value.get("value", default) if row and isinstance(row.value, dict) else default
        items.append(
            AdminSettingView(
                key=key,
                value=json.dumps(value, ensure_ascii=False)
                if not isinstance(value, str)
                else value,
                updated_at=row.updated_at if row else None,
            )
        )
    return items


async def set_setting(
    db: AsyncSession, actor: User, key: str, raw_value: str
) -> AdminSettingView:
    if key not in SETTING_DEFAULTS:
        raise ValidationAppError("Неизвестный параметр", code="unknown_setting")
    try:
        parsed: Any = json.loads(raw_value)
    except json.JSONDecodeError:
        parsed = raw_value
    if key == "free_daily_swipes" and (
        not isinstance(parsed, int) or parsed < 0 or parsed > 1000
    ):
        raise ValidationAppError("Лимит должен быть целым числом от 0 до 1000")
    if key in {"enable_telegram", "enable_glass"} and not isinstance(parsed, bool):
        raise ValidationAppError("Значение должно быть true или false")
    row = await db.get(SystemSetting, key)
    if row is None:
        row = SystemSetting(key=key, value={"value": parsed}, updated_by=actor.id)
        db.add(row)
    else:
        row.value = {"value": parsed}
        row.updated_by = actor.id
    await _audit(
        db,
        actor=actor,
        action="settings.update",
        object_type="setting",
        object_id=key,
        metadata={"value": parsed},
    )
    await db.commit()
    await db.refresh(row)
    return AdminSettingView(
        key=key,
        value=json.dumps(parsed, ensure_ascii=False)
        if not isinstance(parsed, str)
        else parsed,
        updated_at=row.updated_at,
    )


async def audit_log(db: AsyncSession, limit: int = 100) -> list[AdminAuditView]:
    rows = (
        await db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))
    ).all()
    return [
        AdminAuditView(
            id=row.id,
            action=row.action,
            object_type=row.object_type,
            object_id=row.object_id,
            actor_role=row.actor_role,
            metadata=row.metadata_json,
            created_at=row.created_at,
        )
        for row in rows
    ]


async def list_payments(db: AsyncSession) -> list[AdminPaymentView]:
    rows = (
        await db.execute(
            select(PaymentOrder, Plan, Profile)
            .join(Plan, Plan.id == PaymentOrder.plan_id)
            .outerjoin(Profile, Profile.user_id == PaymentOrder.user_id)
            .order_by(PaymentOrder.created_at.desc())
            .limit(200)
        )
    ).all()
    return [
        AdminPaymentView(
            public_id=order.id,
            user_name=display_name(profile),
            plan_code=plan.code,
            provider=order.provider,
            status=order.status,
            amount_kopecks=order.amount_kopecks,
            currency=order.currency,
            created_at=order.created_at,
            paid_at=order.paid_at,
        )
        for order, plan, profile in rows
    ]
