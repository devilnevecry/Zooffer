from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from zooffer.api.deps import CurrentAuth, DbSession
from zooffer.core.enums import ListingPurpose, Sex, Species
from zooffer.core.errors import NotFoundError
from zooffer.schemas.listing import (
    DictionariesResponse,
    DictionaryItem,
    ListingCreateRequest,
    ListingOwnerView,
    ListingUpdateRequest,
    PublishRequest,
)
from zooffer.services import listing_service
from zooffer.services.listing_service import ListingFilters

router = APIRouter(prefix="/listings", tags=["listings"])
public_router = APIRouter(prefix="/public", tags=["public"])

MAX_PAGE = 50


async def _owner_view(db: DbSession, listing) -> ListingOwnerView:  # type: ignore[no-untyped-def]
    from zooffer.db.models import Animal

    animal_public_id = await db.scalar(
        select(Animal.public_id).where(Animal.id == listing.animal_id)
    )
    if animal_public_id is None:
        raise NotFoundError("Животное не найдено", code="animal_not_found")
    return ListingOwnerView(
        public_id=listing.public_id,
        slug=listing.slug,
        title=listing.title,
        description=listing.description,
        purpose=ListingPurpose(listing.purpose),
        status=listing.status,
        price_kopecks=listing.price_kopecks,
        currency=listing.currency,
        negotiable=listing.negotiable,
        city_id=listing.city_id,
        region_id=listing.region_id,
        animal_id=listing.animal_id,
        animal_public_id=animal_public_id,
        published_at=listing.published_at,
        expires_at=listing.expires_at,
        moderation_reason=listing.moderation_reason,
        created_at=listing.created_at,
        updated_at=listing.updated_at,
    )


@router.post("", status_code=201, response_model=ListingOwnerView)
async def create_listing(
    payload: ListingCreateRequest, auth: CurrentAuth, db: DbSession
) -> ListingOwnerView:
    listing = await listing_service.create_listing(db, auth.user, payload)
    return await _owner_view(db, listing)


@router.get("", response_model=list[ListingOwnerView])
async def my_listings(auth: CurrentAuth, db: DbSession) -> list[ListingOwnerView]:
    listings = await listing_service.list_owned_listings(db, auth.user.id)
    return [await _owner_view(db, listing) for listing in listings]


@router.get("/{public_id}", response_model=ListingOwnerView)
async def get_my_listing(
    public_id: uuid.UUID, auth: CurrentAuth, db: DbSession
) -> ListingOwnerView:
    listings = await listing_service.list_owned_listings(db, auth.user.id)
    for listing in listings:
        if listing.public_id == public_id:
            return await _owner_view(db, listing)
    raise NotFoundError("Объявление не найдено", code="listing_not_found")


@router.patch("/{public_id}", response_model=ListingOwnerView)
async def update_listing(
    public_id: uuid.UUID, payload: ListingUpdateRequest, auth: CurrentAuth, db: DbSession
) -> ListingOwnerView:
    listing = await listing_service.update_listing(db, auth.user, public_id, payload)
    return await _owner_view(db, listing)


@router.post("/{public_id}/publish", response_model=ListingOwnerView)
async def publish_listing(
    public_id: uuid.UUID, payload: PublishRequest, auth: CurrentAuth, db: DbSession
) -> ListingOwnerView:
    # Pydantic validates that every consent flag is true before publishing.
    listing = await listing_service.publish_listing(db, auth.user, public_id)
    return await _owner_view(db, listing)


@router.post("/{public_id}/pause", response_model=ListingOwnerView)
async def pause_listing(public_id: uuid.UUID, auth: CurrentAuth, db: DbSession) -> ListingOwnerView:
    return await _owner_view(db, await listing_service.pause_listing(db, auth.user, public_id))


@router.post("/{public_id}/renew", response_model=ListingOwnerView)
async def renew_listing(public_id: uuid.UUID, auth: CurrentAuth, db: DbSession) -> ListingOwnerView:
    return await _owner_view(db, await listing_service.renew_listing(db, auth.user, public_id))


@router.post("/{public_id}/archive", response_model=ListingOwnerView)
async def archive_listing(
    public_id: uuid.UUID, auth: CurrentAuth, db: DbSession
) -> ListingOwnerView:
    return await _owner_view(db, await listing_service.archive_listing(db, auth.user, public_id))


@router.post("/{public_id}/sold", response_model=ListingOwnerView)
async def sold_listing(public_id: uuid.UUID, auth: CurrentAuth, db: DbSession) -> ListingOwnerView:
    return await _owner_view(db, await listing_service.mark_sold(db, auth.user, public_id))


@public_router.get("/listings", response_model=dict)
async def search_listings(
    db: DbSession,
    q: str | None = None,
    purpose: Annotated[list[ListingPurpose] | None, Query()] = None,
    species: Species | None = None,
    breed_id: int | None = None,
    sex: Sex | None = None,
    min_age: int | None = Query(default=None, ge=0, le=60),
    max_age: int | None = Query(default=None, ge=0, le=60),
    size: str | None = None,
    colour: str | None = None,
    city_id: int | None = None,
    region_id: int | None = None,
    price_min: int | None = Query(default=None, ge=0),
    price_max: int | None = Query(default=None, ge=0),
    has_pedigree: bool | None = None,
    vaccinated: bool | None = None,
    with_photos: bool | None = None,
    sort: str = "newest",
    cursor: str | None = None,
    limit: int = Query(default=24, ge=1, le=MAX_PAGE),
) -> dict:
    filters = ListingFilters(
        q=q,
        purposes=purpose,
        species=species,
        breed_id=breed_id,
        sex=sex,
        min_age=min_age,
        max_age=max_age,
        size=size,
        colour=colour,
        city_id=city_id,
        region_id=region_id,
        price_min=price_min,
        price_max=price_max,
        has_pedigree=has_pedigree,
        vaccinated=vaccinated,
        with_photos=with_photos,
        sort=sort,
    )
    items, next_cursor, has_more = await listing_service.search_public_listings(
        db, filters, limit=limit, cursor=cursor
    )
    return {
        "items": [item.model_dump(mode="json") for item in items],
        "next_cursor": next_cursor,
        "has_more": has_more,
    }


@public_router.get("/listings/{slug}", response_model=dict)
async def public_listing(slug: str, db: DbSession) -> dict:
    view = await listing_service.get_public_listing(db, slug)
    await listing_service.record_listing_view(db, view.public_id)
    return view.model_dump(mode="json")


@public_router.get("/home", response_model=dict)
async def homepage(db: DbSession) -> dict:
    featured = await listing_service.get_featured_listings(db, limit=8)
    categories = await listing_service.get_categories(db)
    recent = []
    if not featured:
        recent, _, _ = await listing_service.search_public_listings(db, ListingFilters(), limit=8)
    return {
        "featured": [item.model_dump(mode="json") for item in featured],
        "recent": [item.model_dump(mode="json") for item in recent],
        "categories": categories,
    }


@public_router.get("/dictionaries", response_model=DictionariesResponse)
async def dictionaries(db: DbSession) -> DictionariesResponse:
    from zooffer.db.models import Breed, City, Region

    regions = (await db.scalars(select(Region).order_by(Region.name))).all()
    cities = (await db.scalars(select(City).order_by(City.name))).all()
    breeds = (await db.scalars(select(Breed).order_by(Breed.species, Breed.name))).all()
    return DictionariesResponse(
        regions=[DictionaryItem(id=r.id, name=r.name, slug=r.slug) for r in regions],
        cities=[
            DictionaryItem(id=c.id, name=c.name, slug=c.slug, region_id=c.region_id) for c in cities
        ],
        breeds=[
            DictionaryItem(id=b.id, name=b.name, slug=b.slug, species=b.species) for b in breeds
        ],
    )


@public_router.get("/owners/{public_id}", response_model=dict)
async def public_owner(public_id: uuid.UUID, db: DbSession) -> dict:
    """Deliberately minimal: other users can never fetch an owner profile beyond the name."""
    from zooffer.db.models import Profile, User

    row = (
        await db.execute(
            select(User, Profile)
            .outerjoin(Profile, Profile.user_id == User.id)
            .where(User.public_id == public_id)
        )
    ).first()
    if row is None:
        raise NotFoundError("Владелец не найден", code="owner_not_found")
    _user, profile = row
    from zooffer.services.listing_service import display_name

    return {"display_name": display_name(profile)}
