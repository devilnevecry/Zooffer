from __future__ import annotations

import uuid

from sqlalchemy import func, select

from zooffer.core.errors import ForbiddenError, NotFoundError, ValidationAppError
from zooffer.db.models import Event, EventAttendee, Profile

EVENTTYPES = {"meetup", "show", "training", "webinar", "other"}


async def _get(db, public_id):
    e = await db.scalar(select(Event).where(Event.public_id == public_id))
    if e is None:
        raise NotFoundError("Событие не найдено", code="event_not_found")
    return e


async def _owner_name(db, user_id):
    profile = await db.get(Profile, user_id)
    if profile is None:
        return None
    first = profile.public_first_name
    last = profile.public_last_name
    if first and last:
        return f"{first} {last}"
    return first or last


async def create_event(db, user, payload) -> Event:
    if payload.event_type not in EVENTTYPES:
        raise ValidationAppError("Некорректный тип", code="invalid_type")
    e = Event(
        id=uuid.uuid4(),
        public_id=uuid.uuid4(),
        organizer_id=user.id,
        event_type=payload.event_type,
        title=payload.title.strip(),
        description=payload.description.strip(),
        city_id=payload.city_id,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        location=payload.location,
        capacity=payload.capacity,
        status="draft",
    )
    db.add(e)
    await db.commit()
    await db.refresh(e)
    return e


async def update_event(db, user, public_id, payload) -> Event:
    e = await _get(db, public_id)
    if e.organizer_id != user.id:
        raise ForbiddenError("Нет прав", code="forbidden")
    if payload.event_type is not None:
        if payload.event_type not in EVENTTYPES:
            raise ValidationAppError("Некорректный тип", code="invalid_type")
        e.event_type = payload.event_type
    if payload.title is not None:
        e.title = payload.title.strip()
    if payload.description is not None:
        e.description = payload.description.strip()
    if payload.city_id is not None:
        e.city_id = payload.city_id
    if payload.starts_at is not None:
        e.starts_at = payload.starts_at
    if payload.ends_at is not None:
        e.ends_at = payload.ends_at
    if payload.location is not None:
        e.location = payload.location
    if payload.capacity is not None:
        e.capacity = payload.capacity
    if payload.status is not None:
        if payload.status not in {"draft", "published", "cancelled"}:
            raise ValidationAppError("Некорректный статус", code="invalid_status")
        e.status = payload.status
    await db.commit()
    await db.refresh(e)
    return e


async def publish_event(db, user, public_id) -> Event:
    e = await _get(db, public_id)
    if e.organizer_id != user.id:
        raise ForbiddenError("Нет прав", code="forbidden")
    e.status = "published"
    await db.commit()
    await db.refresh(e)
    return e


async def rsvp(db, user, public_id, status="going") -> EventAttendee:
    e = await _get(db, public_id)
    if e.status != "published":
        raise ValidationAppError("Событие не опубликовано", code="not_published")
    existing = await db.scalar(
        select(EventAttendee).where(
            EventAttendee.event_id == e.id, EventAttendee.user_id == user.id
        )
    )
    if existing is not None:
        existing.status = status
        await db.commit()
        await db.refresh(existing)
        return existing
    if e.capacity is not None:
        count = await db.scalar(
            select(func.count(EventAttendee.id)).where(EventAttendee.event_id == e.id)
        )
        if (count or 0) >= e.capacity:
            raise ValidationAppError("Нет мест", code="full")
    att = EventAttendee(id=uuid.uuid4(), event_id=e.id, user_id=user.id, status=status)
    db.add(att)
    await db.commit()
    await db.refresh(att)
    return att


async def list_events(db, *, city_id=None, status="published", limit=50):
    q = select(Event).where(Event.status == status)
    if city_id is not None:
        q = q.where(Event.city_id == city_id)
    rows = (await db.scalars(q)).all()
    rows = sorted(rows, key=lambda r: r.starts_at)
    return list(rows[:limit])


async def get_event(db, public_id):
    return await _get(db, public_id)


async def event_to_public(db, e) -> dict:
    return {
        "public_id": e.public_id,
        "event_type": e.event_type,
        "title": e.title,
        "description": e.description,
        "city_id": e.city_id,
        "starts_at": e.starts_at,
        "ends_at": e.ends_at,
        "location": e.location,
        "capacity": e.capacity,
        "status": e.status,
        "created_at": e.created_at,
        "organizer": {"display_name": await _owner_name(db, e.organizer_id)},
    }


async def event_to_owner(db, e) -> dict:
    return {
        "public_id": e.public_id,
        "event_type": e.event_type,
        "status": e.status,
        "title": e.title,
        "description": e.description,
        "city_id": e.city_id,
        "starts_at": e.starts_at,
        "ends_at": e.ends_at,
        "location": e.location,
        "capacity": e.capacity,
        "created_at": e.created_at,
        "updated_at": e.updated_at,
    }
