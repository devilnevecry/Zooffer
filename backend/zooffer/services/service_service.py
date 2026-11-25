from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select

from zooffer.core.errors import ForbiddenError, NotFoundError, ValidationAppError
from zooffer.db.models import Profile, ServiceProfile, ServiceReview
from zooffer.schemas.service import (
    ServiceProfileCreateRequest,
    ServiceProfileUpdateRequest,
    ServiceReviewCreateRequest,
)

CATEGORIES = {
    "vet",
    "groomer",
    "trainer",
    "sitter",
    "taxi",
    "photographer",
    "behaviorist",
    "handler",
    "rehab",
}


async def _get_profile(db, public_id):
    p = await db.scalar(select(ServiceProfile).where(ServiceProfile.public_id == public_id))
    if p is None:
        raise NotFoundError("Профиль специалиста не найден", code="service_profile_not_found")
    return p


async def _owner_name(db, user_id):
    profile = await db.get(Profile, user_id)
    if profile is None:
        return None
    first = profile.public_first_name
    last = profile.public_last_name
    if first and last:
        return f"{first} {last}"
    return first or last


async def create_profile(db, user, payload: ServiceProfileCreateRequest) -> ServiceProfile:
    if payload.category not in CATEGORIES:
        raise ValidationAppError("Некорректная категория", code="invalid_category")
    existing = await db.scalar(
        select(ServiceProfile).where(
            ServiceProfile.user_id == user.id, ServiceProfile.category == payload.category
        )
    )
    if existing is not None:
        raise ValidationAppError("Профиль уже существует", code="profile_exists")
    profile = ServiceProfile(
        id=uuid.uuid4(),
        public_id=uuid.uuid4(),
        user_id=user.id,
        category=payload.category,
        title=payload.title.strip(),
        description=payload.description.strip(),
        city_id=payload.city_id,
        price_from_kopecks=payload.price_from_kopecks,
        formats=payload.formats,
        experience_years=payload.experience_years,
        status="pending",
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def update_profile(
    db, user, public_id, payload: ServiceProfileUpdateRequest
) -> ServiceProfile:
    profile = await _get_profile(db, public_id)
    if profile.user_id != user.id:
        raise ForbiddenError("Нет прав на изменение", code="forbidden")
    if payload.title is not None:
        profile.title = payload.title.strip()
    if payload.description is not None:
        profile.description = payload.description.strip()
    if payload.city_id is not None:
        profile.city_id = payload.city_id
    if payload.price_from_kopecks is not None:
        profile.price_from_kopecks = payload.price_from_kopecks
    if payload.formats is not None:
        profile.formats = payload.formats
    if payload.experience_years is not None:
        profile.experience_years = payload.experience_years
    await db.commit()
    await db.refresh(profile)
    return profile


async def verify_profile(db, user, public_id) -> ServiceProfile:
    if getattr(user, "role", None) not in {"admin", "superadmin"}:
        raise ForbiddenError("Недостаточно прав", code="permission_denied")
    profile = await _get_profile(db, public_id)
    profile.verified = True
    profile.verified_at = datetime.now(UTC)
    profile.status = "approved"
    await db.commit()
    await db.refresh(profile)
    return profile


async def list_profiles(
    db,
    *,
    category: str | None = None,
    city_id: int | None = None,
    verified_only: bool = False,
    status: str = "approved",
    limit: int = 50,
) -> list[ServiceProfile]:
    q = select(ServiceProfile).where(ServiceProfile.status == status)
    if category:
        q = q.where(ServiceProfile.category == category)
    if city_id is not None:
        q = q.where(ServiceProfile.city_id == city_id)
    if verified_only:
        q = q.where(ServiceProfile.verified.is_(True))
    rows = (await db.scalars(q)).all()
    rows = sorted(rows, key=lambda r: r.created_at, reverse=True)
    return list(rows[:limit])


async def get_profile(db, public_id):
    return await _get_profile(db, public_id)


async def add_review(db, user, public_id, payload: ServiceReviewCreateRequest) -> ServiceReview:
    profile = await _get_profile(db, public_id)
    if profile.status != "approved":
        raise ValidationAppError("Профиль не опубликован", code="not_approved")
    existing = await db.scalar(
        select(ServiceReview).where(
            ServiceReview.profile_id == profile.id, ServiceReview.author_id == user.id
        )
    )
    if existing is not None:
        raise ValidationAppError("Отзыв уже оставлен", code="review_exists")
    review = ServiceReview(
        id=uuid.uuid4(),
        profile_id=profile.id,
        author_id=user.id,
        booking_ref=payload.booking_ref,
        rating=payload.rating,
        body=payload.body.strip(),
    )
    db.add(review)
    await db.flush()
    # recompute rating
    result = await db.execute(
        select(func.avg(ServiceReview.rating), func.count(ServiceReview.id)).where(
            ServiceReview.profile_id == profile.id
        )
    )
    agg = result.one()
    avg, cnt = agg
    profile.rating_avg = float(avg) if avg is not None else None
    profile.reviews_count = int(cnt or 0)
    await db.commit()
    await db.refresh(review)
    return review


async def list_reviews(db, public_id) -> list[ServiceReview]:
    profile = await _get_profile(db, public_id)
    rows = (
        await db.scalars(
            select(ServiceReview)
            .where(ServiceReview.profile_id == profile.id)
            .order_by(ServiceReview.created_at.desc())
        )
    ).all()
    return list(rows)


async def profile_to_public(db, profile) -> dict[str, Any]:
    return {
        "public_id": profile.public_id,
        "category": profile.category,
        "title": profile.title,
        "description": profile.description,
        "city_id": profile.city_id,
        "price_from_kopecks": profile.price_from_kopecks,
        "formats": profile.formats or [],
        "experience_years": profile.experience_years,
        "verified": profile.verified,
        "rating_avg": float(profile.rating_avg) if profile.rating_avg is not None else None,
        "reviews_count": profile.reviews_count,
        "created_at": profile.created_at,
        "owner": {"display_name": await _owner_name(db, profile.user_id)},
    }


async def profile_to_owner(db, profile) -> dict[str, Any]:
    return {
        "public_id": profile.public_id,
        "category": profile.category,
        "status": profile.status,
        "title": profile.title,
        "description": profile.description,
        "city_id": profile.city_id,
        "price_from_kopecks": profile.price_from_kopecks,
        "formats": profile.formats or [],
        "experience_years": profile.experience_years,
        "verified": profile.verified,
        "rating_avg": float(profile.rating_avg) if profile.rating_avg is not None else None,
        "reviews_count": profile.reviews_count,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }
