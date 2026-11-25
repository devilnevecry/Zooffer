from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from zooffer.api.deps import CurrentAuth, DbSession
from zooffer.schemas.event import (
    EventCreateRequest,
    EventListResponse,
    EventOwnerView,
    EventUpdateRequest,
    PublicEventView,
)
from zooffer.services import event_service

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", status_code=201)
async def create_event(payload: EventCreateRequest, auth: CurrentAuth, db: DbSession) -> dict:
    user = auth.user
    e = await event_service.create_event(db, user, payload)
    return await _owner_payload(db, e)


@router.get("")
async def list_events(
    db: DbSession,
    city_id: int | None = Query(default=None),
    status: str = Query(default="published"),
    limit: int = Query(default=50, le=200),
) -> EventListResponse:
    events = await event_service.list_events(db, city_id=city_id, status=status, limit=limit)
    items = [PublicEventView(**await event_service.event_to_public(db, e)) for e in events]
    return EventListResponse(items=items, meta={"total": len(items)})


@router.get("/{public_id}")
async def get_event(public_id: uuid.UUID, db: DbSession) -> PublicEventView:
    e = await event_service.get_event(db, public_id)
    return PublicEventView(**await event_service.event_to_public(db, e))


@router.patch("/{public_id}")
async def update_event(
    public_id: uuid.UUID, payload: EventUpdateRequest, auth: CurrentAuth, db: DbSession
) -> dict:
    user = auth.user
    e = await event_service.update_event(db, user, public_id, payload)
    return await _owner_payload(db, e)


@router.post("/{public_id}/publish")
async def publish_event(public_id: uuid.UUID, auth: CurrentAuth, db: DbSession) -> dict:
    user = auth.user
    e = await event_service.publish_event(db, user, public_id)
    return await _owner_payload(db, e)


@router.post("/{public_id}/rsvp")
async def rsvp(public_id: uuid.UUID, auth: CurrentAuth, db: DbSession) -> dict:
    user = auth.user
    att = await event_service.rsvp(db, user, public_id)
    return {"status": att.status, "created_at": att.created_at}


async def _owner_payload(db, e) -> dict:
    data = await event_service.event_to_owner(db, e)
    return EventOwnerView(**data).model_dump()
