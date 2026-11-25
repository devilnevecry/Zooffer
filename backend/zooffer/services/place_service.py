from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from zooffer.core.errors import ForbiddenError, NotFoundError, ValidationAppError
from zooffer.db.models import Place, Profile
from zooffer.schemas.place import PlaceCreateRequest, PlaceModerateRequest, PlaceUpdateRequest

EARTH_RADIUS_KM = 6371.0


def _haversine_km(lat1, lon1, lat2, lon2):
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


async def _get_place(db, public_id):
    place = await db.scalar(select(Place).where(Place.public_id == public_id))
    if place is None:
        raise NotFoundError("Место не найдено", code="place_not_found")
    return place


async def _owner_display_name(db, user_id):
    profile = await db.get(Profile, user_id)
    if profile is None:
        return None
    first = profile.public_first_name
    last = profile.public_last_name
    if first and last:
        return f"{first} {last}"
    return first or last


async def create_place(db, user, payload: PlaceCreateRequest) -> Place:
    if payload.category not in {
        "vet_clinic",
        "groomer",
        "park",
        "cafe",
        "dangerous",
        "shelter",
        "other",
    }:
        raise ValidationAppError("Некорректная категория", code="invalid_category")
    place = Place(
        id=uuid.uuid4(),
        public_id=uuid.uuid4(),
        reporter_id=user.id,
        category=payload.category,
        status="pending",
        name=payload.name.strip(),
        description=payload.description.strip(),
        latitude=payload.latitude,
        longitude=payload.longitude,
        city_id=payload.city_id,
    )
    db.add(place)
    await db.commit()
    await db.refresh(place)
    return place


async def get_place(db, public_id):
    return await _get_place(db, public_id)


async def update_place(db, user, public_id, payload: PlaceUpdateRequest) -> Place:
    place = await _get_place(db, public_id)
    if place.reporter_id != user.id:
        raise ForbiddenError("Нет прав на изменение", code="forbidden")
    if place.status != "pending":
        raise ValidationAppError("Только ожидающие модерации", code="not_pending")
    if payload.category is not None:
        if payload.category not in {
            "vet_clinic",
            "groomer",
            "park",
            "cafe",
            "dangerous",
            "shelter",
            "other",
        }:
            raise ValidationAppError("Некорректная категория", code="invalid_category")
        place.category = payload.category
    if payload.name is not None:
        place.name = payload.name.strip()
    if payload.description is not None:
        place.description = payload.description.strip()
    if payload.latitude is not None:
        place.latitude = payload.latitude
    if payload.longitude is not None:
        place.longitude = payload.longitude
    await db.commit()
    await db.refresh(place)
    return place


async def moderate_place(db, user, public_id, payload: PlaceModerateRequest) -> Place:
    if getattr(user, "role", None) not in {"moderator", "admin", "superadmin"}:
        raise ForbiddenError("Недостаточно прав", code="permission_denied")
    place = await _get_place(db, public_id)
    if payload.decision not in {"approve", "reject"}:
        raise ValidationAppError("Некорректное решение", code="invalid_decision")
    place.status = "approved" if payload.decision == "approve" else "rejected"
    place.moderation_reason = payload.reason
    place.moderated_at = datetime.now(UTC)
    place.moderated_by = user.id
    await db.commit()
    await db.refresh(place)
    return place


async def list_places(
    db,
    *,
    category: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    radius_km: float | None = None,
    status: str = "approved",
    limit: int = 100,
) -> list[Place]:
    query = select(Place).where(Place.status == status)
    if category:
        query = query.where(Place.category == category)
    places = (await db.scalars(query)).all()
    if latitude is not None and longitude is not None and radius_km is not None:
        filtered = []
        for p in places:
            dist = _haversine_km(latitude, longitude, float(p.latitude), float(p.longitude))
            if dist <= radius_km:
                filtered.append(p)
        places = filtered
    places = sorted(places, key=lambda p: p.created_at, reverse=True)
    return list(places[:limit])


async def place_to_public(db, place) -> dict:
    owner_name = await _owner_display_name(db, place.reporter_id)
    return {
        "public_id": place.public_id,
        "category": place.category,
        "name": place.name,
        "description": place.description,
        "latitude": float(place.latitude),
        "longitude": float(place.longitude),
        "city_id": place.city_id,
        "created_at": place.created_at,
        "owner": {"display_name": owner_name},
    }


async def place_to_owner(db, place) -> dict:
    return {
        "public_id": place.public_id,
        "category": place.category,
        "status": place.status,
        "name": place.name,
        "description": place.description,
        "latitude": float(place.latitude),
        "longitude": float(place.longitude),
        "city_id": place.city_id,
        "moderation_reason": place.moderation_reason,
        "created_at": place.created_at,
        "updated_at": place.updated_at,
    }
