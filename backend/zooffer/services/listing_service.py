from __future__ import annotations

import base64
import json
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Select, and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from zooffer.core.enums import ListingPurpose, ListingStatus, Sex, Species
from zooffer.core.errors import NotFoundError, ValidationAppError
from zooffer.core.utils import (
    age_years,
    find_contact_matches,
    normalize_whitespace,
    slugify,
    utcnow,
)
from zooffer.db.models import (
    Animal,
    AnimalDocument,
    AnimalPhoto,
    Block,
    Breed,
    City,
    Listing,
    Profile,
    Region,
    Swipe,
    User,
)
from zooffer.schemas.listing import (
    AnimalCreateRequest,
    AnimalUpdateRequest,
    ListingCreateRequest,
    ListingUpdateRequest,
)
from zooffer.schemas.public import (
    PublicAnimalView,
    PublicCityView,
    PublicListingCardView,
    PublicListingView,
    PublicOwnerView,
    PublicPhotoView,
    PublicRegionView,
)
from zooffer.services.media import (
    MAX_IMAGES_PER_ANIMAL,
    media_url,
    process_and_store_image,
    thumb_key_for,
)

MATING_PURPOSES = {ListingPurpose.MATING, ListingPurpose.BREEDING_PEDIGREE}
_MATING_PURPOSE_VALUES = {p.value for p in MATING_PURPOSES}
PUBLISHED = ListingStatus.PUBLISHED.value
PROHIBITED_TERMS = (
    "красная книга",
    "краснокниж",
    "бойцовых собак",
    "собачьи бои",
    "расчленен",
    "жестокое обращение",
    " endangered ",
)
LISTING_LIFETIME = timedelta(days=60)


def display_name(profile: Profile | None) -> str | None:
    if profile is None:
        return None
    parts = [p for p in (profile.public_first_name, profile.public_last_name) if p]
    return " ".join(parts) if parts else None


def _photo_views(photos: list[AnimalPhoto], *, full: bool) -> list[PublicPhotoView]:
    result = []
    for photo in photos:
        key = photo.storage_key if full else thumb_key_for(photo.storage_key)
        result.append(
            PublicPhotoView(
                url=media_url(key),
                alt=photo.alt_text,
                width=photo.width,
                height=photo.height,
                is_primary=photo.is_primary,
            )
        )
    return result


async def _photos_for(db: AsyncSession, animal_ids: list[UUID]) -> dict[UUID, list[AnimalPhoto]]:
    if not animal_ids:
        return {}
    rows = (
        await db.scalars(
            select(AnimalPhoto)
            .where(AnimalPhoto.animal_id.in_(animal_ids))
            .order_by(AnimalPhoto.position.asc())
        )
    ).all()
    grouped: dict[UUID, list[AnimalPhoto]] = {}
    for photo in rows:
        grouped.setdefault(photo.animal_id, []).append(photo)
    return grouped


async def animal_documents_exist(db: AsyncSession, animal_ids: list[UUID]) -> set[UUID]:
    if not animal_ids:
        return set()
    rows = await db.scalars(
        select(AnimalDocument.animal_id).where(AnimalDocument.animal_id.in_(animal_ids))
    )
    return set(rows.all())


async def _get_owned_animal(db: AsyncSession, owner_id: UUID, public_id: UUID) -> Animal:
    animal = await db.scalar(
        select(Animal).where(Animal.public_id == public_id, Animal.owner_id == owner_id)
    )
    if animal is None:
        raise NotFoundError("Животное не найдено", code="animal_not_found")
    return animal


async def get_animal_for_owner(db: AsyncSession, owner_id: UUID, public_id: UUID) -> Animal:
    return await _get_owned_animal(db, owner_id, public_id)


async def create_animal(db: AsyncSession, user: User, payload: AnimalCreateRequest) -> Animal:
    if payload.breed_id is not None:
        breed = await db.get(Breed, payload.breed_id)
        if breed is None or breed.species != payload.species.value:
            raise ValidationAppError("Порода не найдена для выбранного вида", code="invalid_breed")
    animal = Animal(
        id=uuid4(),
        public_id=uuid4(),
        owner_id=user.id,
        name=payload.name,
        species=payload.species.value,
        breed_id=payload.breed_id,
        breed_text=payload.breed_text,
        sex=payload.sex.value,
        birth_date=payload.birth_date,
        colour=payload.colour,
        size=payload.size.value,
        has_pedigree=payload.has_pedigree,
        pedigree_registry=payload.pedigree_registry,
        pedigree_number=payload.pedigree_number,
        vaccinated=payload.vaccinated,
        health_notes=payload.health_notes,
        description=payload.description,
    )
    db.add(animal)
    await db.commit()
    await db.refresh(animal)
    return animal


async def add_animal_photo(
    db: AsyncSession,
    user: User,
    animal_public_id: UUID,
    content: bytes,
) -> AnimalPhoto:
    """Store one validated, re-encoded photo for an owned animal.

    Used by both the HTTP upload endpoint and the bot wizard so limits and
    sanitisation are identical across channels.
    """
    animal = await _get_owned_animal(db, user.id, animal_public_id)
    count = await db.scalar(
        select(func.count()).select_from(AnimalPhoto).where(AnimalPhoto.animal_id == animal.id)
    )
    if int(count or 0) >= MAX_IMAGES_PER_ANIMAL:
        raise ValidationAppError(
            f"Можно загрузить не более {MAX_IMAGES_PER_ANIMAL} фотографий",
            code="photo_limit",
        )
    processed = await process_and_store_image(content)
    position = int(count or 0)
    photo = AnimalPhoto(
        id=uuid4(),
        animal_id=animal.id,
        storage_key=processed.full_key,
        position=position,
        width=processed.width,
        height=processed.height,
        content_hash=processed.content_hash,
        is_primary=position == 0,
        alt_text=animal.name,
    )
    db.add(photo)
    await db.commit()
    return photo


async def update_animal(
    db: AsyncSession, user: User, public_id: UUID, payload: AnimalUpdateRequest
) -> Animal:
    animal = await _get_owned_animal(db, user.id, public_id)
    changes = payload.model_dump(exclude_unset=True)
    if "breed_id" in changes and changes["breed_id"] is not None:
        breed = await db.get(Breed, changes["breed_id"])
        if breed is None or breed.species != animal.species:
            raise ValidationAppError("Порода не найдена для выбранного вида", code="invalid_breed")
    for key, value in changes.items():
        if key == "sex" and value is not None:
            value = value.value if hasattr(value, "value") else value
        if key == "size" and value is not None:
            value = value.value if hasattr(value, "value") else value
        if key == "name" and value is not None:
            value = normalize_whitespace(value)
        setattr(animal, key, value)
    if animal.has_pedigree is False:
        animal.pedigree_registry = None
        animal.pedigree_number = None
    await db.commit()
    await db.refresh(animal)
    return animal


async def list_owned_animals(db: AsyncSession, owner_id: UUID) -> list[Animal]:
    return list(
        (
            await db.scalars(
                select(Animal)
                .where(Animal.owner_id == owner_id, Animal.archived_at.is_(None))
                .order_by(Animal.created_at.desc())
            )
        ).all()
    )


def _listing_slug(title: str, public_id: UUID) -> str:
    return f"{slugify(title, max_length=100)}-{public_id.hex[:8]}"


async def _validate_location(
    db: AsyncSession, city_id: int | None, region_id: int | None
) -> int | None:
    if city_id is None:
        return region_id
    city = await db.get(City, city_id)
    if city is None:
        raise ValidationAppError("Город не найден", code="invalid_city")
    if region_id is not None and region_id != city.region_id:
        raise ValidationAppError("Город не относится к выбранному региону", code="invalid_region")
    return city.region_id


async def create_listing(db: AsyncSession, user: User, payload: ListingCreateRequest) -> Listing:
    animal = await _get_owned_animal(db, user.id, payload.animal_id)
    region_id = await _validate_location(db, payload.city_id, payload.region_id)
    public_id = uuid4()
    listing = Listing(
        id=uuid4(),
        public_id=public_id,
        slug=_listing_slug(payload.title, public_id),
        owner_id=user.id,
        animal_id=animal.id,
        purpose=payload.purpose.value,
        status=ListingStatus.DRAFT.value,
        title=payload.title,
        description=payload.description.strip(),
        breed_text=animal.breed_text,
        price_kopecks=payload.price_kopecks,
        negotiable=payload.negotiable,
        city_id=payload.city_id,
        region_id=region_id,
    )
    db.add(listing)
    await db.commit()
    await db.refresh(listing)
    return listing


async def update_listing(
    db: AsyncSession, user: User, public_id: UUID, payload: ListingUpdateRequest
) -> Listing:
    listing = await _get_owned_listing(db, user.id, public_id)
    if listing.status in {ListingStatus.PUBLISHED.value, ListingStatus.PENDING_MODERATION.value}:
        # Published edits return to moderation to prevent bait-and-switch.
        listing.status = ListingStatus.DRAFT.value
        listing.published_at = None
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("title"):
        changes["title"] = normalize_whitespace(changes["title"])
        listing.slug = _listing_slug(changes["title"], listing.public_id)
    if "city_id" in changes or "region_id" in changes:
        region_id = await _validate_location(
            db, changes.get("city_id", listing.city_id), changes.get("region_id", listing.region_id)
        )
        changes["region_id"] = region_id
    for key, value in changes.items():
        setattr(listing, key, value)
    await db.commit()
    await db.refresh(listing)
    return listing


async def _get_owned_listing(db: AsyncSession, owner_id: UUID, public_id: UUID) -> Listing:
    listing = await db.scalar(
        select(Listing).where(Listing.public_id == public_id, Listing.owner_id == owner_id)
    )
    if listing is None:
        raise NotFoundError("Объявление не найдено", code="listing_not_found")
    return listing


def _quality_score(listing: Listing, photo_count: int, animal: Animal) -> int:
    score = min(photo_count, 10) * 8
    score += min(len(listing.description) // 80, 10)
    if listing.price_kopecks is not None:
        score += 4
    if animal.has_pedigree:
        score += 6
    if animal.vaccinated:
        score += 3
    if listing.city_id:
        score += 3
    return score


def _moderation_issues(listing: Listing, animal: Animal) -> list[str]:
    issues = find_contact_matches(listing.title + " " + listing.description)
    text = (listing.title + " " + listing.description).lower()
    for term in PROHIBITED_TERMS:
        if term in text:
            issues.append("prohibited_content")
            break
    is_sale = listing.purpose == ListingPurpose.SALE.value
    if is_sale and not listing.price_kopecks and not listing.negotiable:
        issues.append("missing_price")
    if animal.has_pedigree and not animal.pedigree_registry:
        issues.append("missing_pedigree_registry")
    return issues


async def publish_listing(db: AsyncSession, user: User, public_id: UUID) -> Listing:
    listing = await _get_owned_listing(db, user.id, public_id)
    if listing.status not in {
        ListingStatus.DRAFT.value,
        ListingStatus.PENDING_MODERATION.value,
        ListingStatus.PAUSED.value,
        ListingStatus.REJECTED.value,
        ListingStatus.EXPIRED.value,
    }:
        raise ValidationAppError("Это объявление нельзя опубликовать", code="invalid_status")
    animal = await db.get(Animal, listing.animal_id)
    if animal is None or animal.archived_at is not None:
        raise ValidationAppError("Анкета животного недоступна", code="animal_unavailable")
    photo_count = await db.scalar(
        select(func.count()).select_from(AnimalPhoto).where(AnimalPhoto.animal_id == animal.id)
    )
    if not photo_count:
        raise ValidationAppError("Добавьте хотя бы одну фотографию", code="photo_required")
    issues = _moderation_issues(listing, animal)
    listing.quality_score = _quality_score(listing, int(photo_count), animal)
    listing.moderated_at = utcnow()
    if issues:
        listing.status = ListingStatus.PENDING_MODERATION.value
        listing.moderation_reason = "Объявление отправлено на проверку: " + ", ".join(
            sorted(set(issues))
        )
    else:
        listing.status = PUBLISHED
        listing.moderation_reason = None
        listing.published_at = utcnow()
        listing.expires_at = utcnow() + LISTING_LIFETIME
    await db.commit()
    await db.refresh(listing)
    return listing


async def pause_listing(db: AsyncSession, user: User, public_id: UUID) -> Listing:
    listing = await _get_owned_listing(db, user.id, public_id)
    if listing.status != PUBLISHED:
        raise ValidationAppError("Приостановить можно только опубликованное объявление")
    listing.status = ListingStatus.PAUSED.value
    listing.paused_at = utcnow()
    await db.commit()
    await db.refresh(listing)
    return listing


async def renew_listing(db: AsyncSession, user: User, public_id: UUID) -> Listing:
    listing = await _get_owned_listing(db, user.id, public_id)
    if listing.status not in {ListingStatus.EXPIRED.value, ListingStatus.PAUSED.value}:
        raise ValidationAppError("Продлить можно истёкшее или приостановленное объявление")
    return await publish_listing(db, user, public_id)


async def archive_listing(db: AsyncSession, user: User, public_id: UUID) -> Listing:
    listing = await _get_owned_listing(db, user.id, public_id)
    listing.status = ListingStatus.ARCHIVED.value
    listing.archived_at = utcnow()
    await db.commit()
    await db.refresh(listing)
    return listing


async def mark_sold(db: AsyncSession, user: User, public_id: UUID) -> Listing:
    listing = await _get_owned_listing(db, user.id, public_id)
    listing.status = ListingStatus.SOLD.value
    listing.sold_at = utcnow()
    await db.commit()
    await db.refresh(listing)
    return listing


async def list_owned_listings(db: AsyncSession, owner_id: UUID) -> list[Listing]:
    return list(
        (
            await db.scalars(
                select(Listing)
                .where(Listing.owner_id == owner_id)
                .order_by(Listing.created_at.desc())
            )
        ).all()
    )


# --- Public read paths -----------------------------------------------------------------------


class ListingFilters:
    def __init__(
        self,
        *,
        q: str | None = None,
        purposes: list[ListingPurpose] | None = None,
        species: Species | None = None,
        breed_id: int | None = None,
        sex: Sex | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
        size: str | None = None,
        colour: str | None = None,
        city_id: int | None = None,
        region_id: int | None = None,
        price_min: int | None = None,
        price_max: int | None = None,
        has_pedigree: bool | None = None,
        vaccinated: bool | None = None,
        with_photos: bool | None = None,
        sort: str = "newest",
    ) -> None:
        self.q = q.strip()[:120] if q else None
        self.purposes = purposes or []
        self.species = species
        self.breed_id = breed_id
        self.sex = sex
        self.min_age = min_age
        self.max_age = max_age
        self.size = size
        self.colour = colour
        self.city_id = city_id
        self.region_id = region_id
        self.price_min = price_min
        self.price_max = price_max
        self.has_pedigree = has_pedigree
        self.vaccinated = vaccinated
        self.with_photos = with_photos
        self.sort = sort if sort in {"newest", "price_asc", "price_desc", "relevance"} else "newest"


def encode_cursor(values: dict[str, Any]) -> str:
    raw = json.dumps(values, separators=(",", ":"), ensure_ascii=False).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> dict[str, Any]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
    except Exception as exc:
        raise ValidationAppError("Некорректный курсор", code="invalid_cursor") from exc
    if not isinstance(data, dict):
        raise ValidationAppError("Некорректный курсор", code="invalid_cursor")
    return data


def _apply_filters(stmt: Select, filters: ListingFilters, now: datetime) -> Select:
    stmt = stmt.where(
        Listing.status == PUBLISHED,
        Listing.deleted_at.is_(None),
        or_(Listing.expires_at.is_(None), Listing.expires_at > now),
    )
    if filters.q:
        tsquery = func.websearch_to_tsquery("russian", filters.q)
        stmt = stmt.where(
            or_(
                Listing.search_vector.op("@@")(tsquery),
                Listing.title.ilike(f"%{filters.q}%"),
            )
        )
    if filters.purposes:
        stmt = stmt.where(Listing.purpose.in_([p.value for p in filters.purposes]))
    if filters.species:
        stmt = stmt.where(Animal.species == filters.species.value)
    if filters.breed_id:
        stmt = stmt.where(Animal.breed_id == filters.breed_id)
    if filters.sex:
        stmt = stmt.where(Animal.sex == filters.sex.value)
    today = now.date()
    if filters.min_age is not None:
        stmt = stmt.where(Animal.birth_date <= today - timedelta(days=365 * filters.min_age))
    if filters.max_age is not None:
        stmt = stmt.where(Animal.birth_date >= today - timedelta(days=365 * (filters.max_age + 1)))
    if filters.size:
        stmt = stmt.where(Animal.size == filters.size)
    if filters.colour:
        stmt = stmt.where(Animal.colour.ilike(f"%{filters.colour[:40]}%"))
    if filters.city_id:
        stmt = stmt.where(Listing.city_id == filters.city_id)
    if filters.region_id:
        stmt = stmt.where(Listing.region_id == filters.region_id)
    if filters.price_min is not None:
        stmt = stmt.where(Listing.price_kopecks >= filters.price_min)
    if filters.price_max is not None:
        stmt = stmt.where(Listing.price_kopecks <= filters.price_max)
    if filters.has_pedigree is not None:
        stmt = stmt.where(Animal.has_pedigree.is_(filters.has_pedigree))
    if filters.vaccinated is not None:
        stmt = stmt.where(Animal.vaccinated.is_(filters.vaccinated))
    if filters.with_photos:
        stmt = stmt.where(select(AnimalPhoto.id).where(AnimalPhoto.animal_id == Animal.id).exists())
    return stmt


def _base_public_query() -> Select:
    return (
        select(Listing, Animal, Profile, City, Region, User)
        .join(Animal, Animal.id == Listing.animal_id)
        .join(User, User.id == Listing.owner_id)
        .outerjoin(Profile, Profile.user_id == Listing.owner_id)
        .outerjoin(City, City.id == Listing.city_id)
        .outerjoin(Region, Region.id == Listing.region_id)
    )


def _apply_keyset(stmt: Select, filters: ListingFilters, cursor: dict[str, Any] | None) -> Select:
    if not cursor:
        return stmt
    try:
        if filters.sort in {"price_asc", "price_desc"}:
            price = int(cursor["p"])
            ident = UUID(str(cursor["i"]))
            price_expr = func.coalesce(Listing.price_kopecks, 2_147_483_647)
            if filters.sort == "price_asc":
                return stmt.where(
                    or_(price_expr > price, and_(price_expr == price, Listing.id > ident))
                )
            return stmt.where(
                or_(price_expr < price, and_(price_expr == price, Listing.id < ident))
            )
        published = datetime.fromisoformat(str(cursor["p"]))
        if published.tzinfo is None:
            published = published.replace(tzinfo=UTC)
        featured = bool(cursor["f"])
        ident = UUID(str(cursor["i"]))
        return stmt.where(
            or_(
                Listing.is_featured < featured,
                and_(Listing.is_featured == featured, Listing.published_at < published),
                and_(
                    Listing.is_featured == featured,
                    Listing.published_at == published,
                    Listing.id < ident,
                ),
            )
        )
    except (KeyError, ValueError) as exc:
        raise ValidationAppError("Некорректный курсор", code="invalid_cursor") from exc


def _next_cursor(filters: ListingFilters, listing: Listing) -> str:
    if filters.sort in {"price_asc", "price_desc"}:
        price = listing.price_kopecks if listing.price_kopecks is not None else 2_147_483_647
        return encode_cursor({"p": price, "i": str(listing.id)})
    return encode_cursor(
        {
            "f": listing.is_featured,
            "p": (listing.published_at or utcnow()).isoformat(),
            "i": str(listing.id),
        }
    )


def _order(stmt: Select, filters: ListingFilters) -> Select:
    if filters.sort == "price_asc":
        return stmt.order_by(
            func.coalesce(Listing.price_kopecks, 2_147_483_647).asc(), Listing.id.asc()
        )
    if filters.sort == "price_desc":
        return stmt.order_by(
            func.coalesce(Listing.price_kopecks, 2_147_483_647).desc(), Listing.id.desc()
        )
    return stmt.order_by(Listing.is_featured.desc(), Listing.published_at.desc(), Listing.id.desc())


def _card_from_row(
    listing: Listing,
    animal: Animal,
    profile: Profile | None,
    city: City | None,
    photos: list[AnimalPhoto],
    *,
    has_document: bool,
) -> PublicListingCardView:
    primary = next((p for p in photos if p.is_primary), photos[0] if photos else None)
    return PublicListingCardView(
        public_id=listing.public_id,
        slug=listing.slug,
        title=listing.title,
        purpose=ListingPurpose(listing.purpose),
        price_kopecks=listing.price_kopecks,
        currency=listing.currency,
        negotiable=listing.negotiable,
        city=PublicCityView(name=city.name, slug=city.slug) if city else None,
        primary_photo=(
            PublicPhotoView(
                url=media_url(thumb_key_for(primary.storage_key)),
                alt=primary.alt_text,
                width=primary.width,
                height=primary.height,
                is_primary=primary.is_primary,
            )
            if primary
            else None
        ),
        animal_name=animal.name,
        species=Species(animal.species),
        breed=animal.breed_text,
        sex=animal.sex,
        age_years=age_years(animal.birth_date),
        has_pedigree=animal.has_pedigree,
        has_pedigree_document=has_document,
        is_featured=listing.is_featured,
        published_at=listing.published_at,
        owner=PublicOwnerView(display_name=display_name(profile)),
    )


async def search_public_listings(
    db: AsyncSession,
    filters: ListingFilters,
    *,
    limit: int = 24,
    cursor: str | None = None,
    exclude_owner_id: UUID | None = None,
    exclude_swiped_for: UUID | None = None,
    exclude_blocked_for: UUID | None = None,
) -> tuple[list[PublicListingCardView], str | None, bool]:
    now = utcnow()
    stmt = _apply_filters(_base_public_query(), filters, now)
    if exclude_owner_id:
        stmt = stmt.where(Listing.owner_id != exclude_owner_id)
    if exclude_swiped_for:
        swiped = select(Swipe.target_id).where(
            Swipe.user_id == exclude_swiped_for, Swipe.target_kind == "listing"
        )
        stmt = stmt.where(Listing.id.notin_(swiped))
    if exclude_blocked_for:
        blocks = select(Block.blocked_id).where(Block.blocker_id == exclude_blocked_for)
        reverse = select(Block.blocker_id).where(Block.blocked_id == exclude_blocked_for)
        stmt = stmt.where(Listing.owner_id.notin_(blocks), Listing.owner_id.notin_(reverse))
    stmt = _apply_keyset(stmt, filters, decode_cursor(cursor) if cursor else None)
    stmt = _order(stmt, filters).limit(limit + 1)
    rows = (await db.execute(stmt)).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    animal_ids = [row[1].id for row in rows]
    photos = await _photos_for(db, animal_ids)
    documents = await animal_documents_exist(db, animal_ids)
    cards = [
        _card_from_row(
            listing,
            animal,
            profile,
            city,
            photos.get(animal.id, []),
            has_document=animal.id in documents,
        )
        for listing, animal, profile, city, _region, _user in rows
    ]
    next_cursor = _next_cursor(filters, rows[-1][0]) if rows and has_more else None
    return cards, next_cursor, has_more


async def get_public_listing(db: AsyncSession, slug_or_id: str) -> PublicListingView:
    stmt = _base_public_query().where(
        Listing.status == PUBLISHED,
        Listing.deleted_at.is_(None),
        or_(Listing.expires_at.is_(None), Listing.expires_at > utcnow()),
        or_(Listing.slug == slug_or_id, Listing.public_id == _try_uuid(slug_or_id)),
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        raise NotFoundError("Объявление не найдено", code="listing_not_found")
    listing, animal, profile, city, region, _owner = row
    photos = (await _photos_for(db, [animal.id])).get(animal.id, [])
    documents = await animal_documents_exist(db, [animal.id])
    return PublicListingView(
        public_id=listing.public_id,
        slug=listing.slug,
        title=listing.title,
        description=listing.description,
        purpose=ListingPurpose(listing.purpose),
        price_kopecks=listing.price_kopecks,
        currency=listing.currency,
        negotiable=listing.negotiable,
        city=PublicCityView(name=city.name, slug=city.slug) if city else None,
        region=PublicRegionView(name=region.name, slug=region.slug) if region else None,
        published_at=listing.published_at,
        expires_at=listing.expires_at,
        is_featured=listing.is_featured,
        animal=PublicAnimalView(
            public_id=animal.public_id,
            name=animal.name,
            species=Species(animal.species),
            breed=animal.breed_text,
            sex=animal.sex,
            age_years=age_years(animal.birth_date),
            birth_date=animal.birth_date,
            colour=animal.colour,
            size=animal.size,
            has_pedigree=animal.has_pedigree,
            pedigree_registry=animal.pedigree_registry,
            vaccinated=animal.vaccinated,
            health_notes=animal.health_notes,
            description=animal.description,
            photos=_photo_views(photos, full=True),
            has_pedigree_document=animal.id in documents,
        ),
        owner=PublicOwnerView(display_name=display_name(profile)),
    )


def _try_uuid(value: str) -> UUID | None:
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        return None


async def record_listing_view(db: AsyncSession, public_id: UUID) -> None:
    await db.execute(
        update(Listing)
        .where(Listing.public_id == public_id)
        .values(views_count=Listing.views_count + 1)
    )
    await db.commit()


async def get_featured_listings(db: AsyncSession, limit: int = 8) -> list[PublicListingCardView]:
    filters = ListingFilters()
    now = utcnow()
    stmt = _apply_filters(_base_public_query(), filters, now).where(Listing.is_featured.is_(True))
    stmt = stmt.order_by(Listing.quality_score.desc(), Listing.published_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).all()
    animal_ids = [row[1].id for row in rows]
    photos = await _photos_for(db, animal_ids)
    documents = await animal_documents_exist(db, animal_ids)
    return [
        _card_from_row(
            listing,
            animal,
            profile,
            city,
            photos.get(animal.id, []),
            has_document=animal.id in documents,
        )
        for listing, animal, profile, city, _region, _user in rows
    ]


async def get_categories(db: AsyncSession) -> list[dict[str, Any]]:
    rows = await db.execute(
        select(Listing.purpose, func.count())
        .where(
            Listing.status == PUBLISHED,
            Listing.deleted_at.is_(None),
            or_(Listing.expires_at.is_(None), Listing.expires_at > utcnow()),
        )
        .group_by(Listing.purpose)
    )
    counts: dict[str, int] = {}
    for purpose, count in rows.all():
        counts[purpose] = count
    return [
        {"purpose": purpose.value, "count": counts.get(purpose.value, 0)}
        for purpose in ListingPurpose
    ]


async def get_listing_owner_id(db: AsyncSession, animal_id: UUID) -> UUID | None:
    return await db.scalar(select(Animal.owner_id).where(Animal.id == animal_id))


def is_mating_purpose(purpose: str) -> bool:
    return purpose in _MATING_PURPOSE_VALUES


def compatible_for_mating(a: Animal, b: Animal) -> bool:
    if a.owner_id == b.owner_id:
        return False
    if a.species != b.species:
        return False
    same_known_sex = a.sex in {"male", "female"} and b.sex in {"male", "female"} and a.sex == b.sex
    return not same_known_sex


def animal_age(birth_date: date | None) -> int | None:
    return age_years(birth_date)
