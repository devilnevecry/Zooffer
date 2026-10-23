from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from zooffer.api.deps import CurrentAuth, DbSession, OptionalAuth
from zooffer.core.enums import ListingPurpose, Species
from zooffer.core.utils import next_quota_reset
from zooffer.schemas.discovery import (
    DiscoveryFeedResponse,
    QuotaView,
    SwipeRequest,
    SwipeResponse,
    UndoResponse,
)
from zooffer.services import listing_service, quota_service, swipe_service
from zooffer.services.listing_service import ListingFilters

router = APIRouter(tags=["discovery"])

GUEST_PREVIEW_LIMIT = 12


def _quota_view(status: quota_service.QuotaStatus) -> QuotaView:
    return QuotaView(
        limit=status.limit,
        used=status.used,
        remaining=status.remaining,
        resets_at=status.resets_at,
        unlimited=status.unlimited,
    )


@router.get("/discovery/feed", response_model=DiscoveryFeedResponse)
async def discovery_feed(
    db: DbSession,
    auth: OptionalAuth,
    purpose: Annotated[list[ListingPurpose] | None, Query()] = None,
    species: Species | None = None,
    city_id: int | None = None,
    breed_id: int | None = None,
    sex: str | None = None,
    cursor: str | None = None,
    limit: int = Query(default=12, ge=1, le=40),
) -> DiscoveryFeedResponse:
    filters = ListingFilters(
        purposes=purpose, species=species, city_id=city_id, breed_id=breed_id, sex=None
    )
    if sex:
        from zooffer.core.enums import Sex

        try:
            filters.sex = Sex(sex)
        except ValueError:
            filters.sex = None
    if auth is None:
        items, next_cursor, has_more = await listing_service.search_public_listings(
            db, filters, limit=min(limit, GUEST_PREVIEW_LIMIT)
        )
        return DiscoveryFeedResponse(
            items=items,
            next_cursor=next_cursor,
            has_more=False,
            quota=QuotaView(
                limit=0,
                used=0,
                remaining=0,
                resets_at=next_quota_reset(),
            ),
            guest=True,
        )
    items, next_cursor, has_more = await listing_service.search_public_listings(
        db,
        filters,
        limit=limit,
        cursor=cursor,
        exclude_owner_id=auth.user.id,
        exclude_swiped_for=auth.user.id,
        exclude_blocked_for=auth.user.id,
    )
    quota = await quota_service.get_quota(db, auth.user.id)
    return DiscoveryFeedResponse(
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
        quota=_quota_view(quota),
    )


@router.post("/discovery/swipes", response_model=SwipeResponse)
async def create_swipe(payload: SwipeRequest, auth: CurrentAuth, db: DbSession) -> SwipeResponse:
    return await swipe_service.swipe(
        db,
        auth.user,
        listing_public_id=payload.listing_public_id,
        action=payload.action,
        request_id=payload.request_id,
        source=payload.source,
    )


@router.post("/discovery/undo", response_model=UndoResponse)
async def undo(auth: CurrentAuth, db: DbSession) -> UndoResponse:
    status = await swipe_service.undo_last_swipe(db, auth.user)
    return UndoResponse(
        undone=True,
        quota_restored=not status.unlimited,
        quota=_quota_view(status),
    )


@router.get("/discovery/quota", response_model=QuotaView)
async def quota(auth: CurrentAuth, db: DbSession) -> QuotaView:
    return _quota_view(await quota_service.get_quota(db, auth.user.id))


favorites_router = APIRouter(prefix="/favorites", tags=["favorites"])


@favorites_router.get("", response_model=dict)
async def list_favorites(auth: CurrentAuth, db: DbSession) -> dict:
    from zooffer.db.models import AnimalPhoto
    from zooffer.services.media import media_url, thumb_key_for

    rows = await swipe_service.list_favorites(db, auth.user)
    items = []
    for listing, animal in rows:
        photo = await db.scalar(
            select(AnimalPhoto)
            .where(AnimalPhoto.animal_id == animal.id)
            .order_by(AnimalPhoto.is_primary.desc(), AnimalPhoto.position.asc())
            .limit(1)
        )
        items.append(
            {
                "public_id": str(listing.public_id),
                "slug": listing.slug,
                "title": listing.title,
                "status": listing.status,
                "purpose": listing.purpose,
                "price_kopecks": listing.price_kopecks,
                "animal_name": animal.name,
                "species": animal.species,
                "primary_photo_url": (
                    media_url(thumb_key_for(photo.storage_key)) if photo is not None else None
                ),
            }
        )
    return {"items": items}


@favorites_router.post("/{listing_public_id}", response_model=dict)
async def add_favorite(listing_public_id: uuid.UUID, auth: CurrentAuth, db: DbSession) -> dict:
    await swipe_service.add_favorite(db, auth.user, listing_public_id)
    return {"ok": True}


@favorites_router.delete("/{listing_public_id}", response_model=dict)
async def remove_favorite(listing_public_id: uuid.UUID, auth: CurrentAuth, db: DbSession) -> dict:
    await swipe_service.remove_favorite(db, auth.user, listing_public_id)
    return {"ok": True}
