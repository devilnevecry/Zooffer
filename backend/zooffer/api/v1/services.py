from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from zooffer.api.deps import CurrentAuth, DbSession, OptionalAuth
from zooffer.core.errors import ForbiddenError
from zooffer.schemas.service import (
    PublicServiceOwnerView,
    PublicServiceProfileView,
    ServiceProfileCreateRequest,
    ServiceProfileListResponse,
    ServiceProfileOwnerView,
    ServiceProfileUpdateRequest,
    ServiceReviewCreateRequest,
    ServiceReviewListResponse,
    ServiceReviewView,
)
from zooffer.services import service_service

router = APIRouter(prefix="/services", tags=["services"])


@router.post("/profiles", status_code=201)
async def create_profile(
    payload: ServiceProfileCreateRequest, auth: CurrentAuth, db: DbSession
) -> dict:
    user = auth.user
    profile = await service_service.create_profile(db, user, payload)
    return await _owner_payload(db, profile)


@router.get("/profiles")
async def list_profiles(
    db: DbSession,
    auth: OptionalAuth = None,
    category: str | None = Query(default=None),
    city_id: int | None = Query(default=None),
    verified_only: bool = Query(default=False),
    status: str = Query(default="approved"),
    limit: int = Query(default=50, le=200),
) -> ServiceProfileListResponse:
    if status != "approved" and (
        auth is None or getattr(auth.user, "role", None) not in {"admin", "superadmin"}
    ):
        raise ForbiddenError("Недостаточно прав", code="permission_denied")
    profiles = await service_service.list_profiles(
        db,
        category=category,
        city_id=city_id,
        verified_only=verified_only,
        status=status,
        limit=limit,
    )
    items = [
        PublicServiceProfileView(**await service_service.profile_to_public(db, p)) for p in profiles
    ]
    return ServiceProfileListResponse(items=items, meta={"total": len(items)})


@router.get("/profiles/{public_id}")
async def get_profile(public_id: uuid.UUID, db: DbSession) -> PublicServiceProfileView:
    profile = await service_service.get_profile(db, public_id)
    return PublicServiceProfileView(**await service_service.profile_to_public(db, profile))


@router.patch("/profiles/{public_id}")
async def update_profile(
    public_id: uuid.UUID, payload: ServiceProfileUpdateRequest, auth: CurrentAuth, db: DbSession
) -> dict:
    user = auth.user
    profile = await service_service.update_profile(db, user, public_id, payload)
    return await _owner_payload(db, profile)


@router.post("/profiles/{public_id}/verify")
async def verify_profile(public_id: uuid.UUID, auth: CurrentAuth, db: DbSession) -> dict:
    user = auth.user
    profile = await service_service.verify_profile(db, user, public_id)
    return await _owner_payload(db, profile)


@router.post("/profiles/{public_id}/reviews", status_code=201)
async def add_review(
    public_id: uuid.UUID, payload: ServiceReviewCreateRequest, auth: CurrentAuth, db: DbSession
) -> dict:
    user = auth.user
    review = await service_service.add_review(db, user, public_id, payload)
    await service_service.get_profile(db, public_id)
    return {
        "id": review.id,
        "rating": review.rating,
        "body": review.body,
        "created_at": review.created_at,
        "author": {"display_name": await _author_name(db, review.author_id)},
    }


@router.get("/profiles/{public_id}/reviews")
async def list_reviews(public_id: uuid.UUID, db: DbSession) -> ServiceReviewListResponse:
    reviews = await service_service.list_reviews(db, public_id)
    items = []
    for r in reviews:
        items.append(
            ServiceReviewView(
                id=r.id,
                rating=r.rating,
                body=r.body,
                created_at=r.created_at,
                author=PublicServiceOwnerView(display_name=await _author_name(db, r.author_id)),
            )
        )
    return ServiceReviewListResponse(items=items, meta={"total": len(items)})


async def _owner_payload(db, profile) -> dict:
    data = await service_service.profile_to_owner(db, profile)
    return ServiceProfileOwnerView(**data).model_dump()


async def _author_name(db, user_id) -> str | None:
    from zooffer.db.models import Profile

    profile = await db.get(Profile, user_id)
    if profile is None:
        return None
    first = profile.public_first_name
    last = profile.public_last_name
    if first and last:
        return f"{first} {last}"
    return first or last
