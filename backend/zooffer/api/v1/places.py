from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from zooffer.api.deps import CurrentAuth, DbSession, OptionalAuth
from zooffer.core.errors import ForbiddenError
from zooffer.schemas.place import (
    PlaceCreateRequest,
    PlaceListResponse,
    PlaceModerateRequest,
    PlaceOwnerView,
    PlaceUpdateRequest,
    PublicPlaceView,
)
from zooffer.services import place_service

router = APIRouter(prefix="/places", tags=["places"])


@router.post("", status_code=201)
async def create_place(payload: PlaceCreateRequest, auth: CurrentAuth, db: DbSession) -> dict:
    user = auth.user
    place = await place_service.create_place(db, user, payload)
    return await _owner_payload(db, place)


@router.get("")
async def list_places(
    db: DbSession,
    auth: OptionalAuth = None,
    category: str | None = Query(default=None),
    latitude: float | None = Query(default=None),
    longitude: float | None = Query(default=None),
    radius_km: float | None = Query(default=None),
    status: str = Query(default="approved"),
    limit: int = Query(default=100, le=200),
) -> PlaceListResponse:
    if status != "approved" and (
        auth is None or getattr(auth.user, "role", None) not in {"moderator", "admin", "superadmin"}
    ):
        raise ForbiddenError("Недостаточно прав", code="permission_denied")
    places = await place_service.list_places(
        db,
        category=category,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        status=status,
        limit=limit,
    )
    items = [PublicPlaceView(**await place_service.place_to_public(db, p)) for p in places]
    return PlaceListResponse(items=items, meta={"total": len(items)})


@router.get("/{public_id}")
async def get_place(public_id: uuid.UUID, db: DbSession) -> PublicPlaceView:
    place = await place_service.get_place(db, public_id)
    return PublicPlaceView(**await place_service.place_to_public(db, place))


@router.patch("/{public_id}")
async def update_place(
    public_id: uuid.UUID, payload: PlaceUpdateRequest, auth: CurrentAuth, db: DbSession
) -> dict:
    user = auth.user
    place = await place_service.update_place(db, user, public_id, payload)
    return await _owner_payload(db, place)


@router.post("/{public_id}/moderate")
async def moderate_place(
    public_id: uuid.UUID, payload: PlaceModerateRequest, auth: CurrentAuth, db: DbSession
) -> dict:
    user = auth.user
    if getattr(user, "role", None) not in {"moderator", "admin", "superadmin"}:
        raise ForbiddenError("Недостаточно прав", code="permission_denied")
    place = await place_service.moderate_place(db, user, public_id, payload)
    return await _owner_payload(db, place)


async def _owner_payload(db: DbSession, place) -> dict:
    data = await place_service.place_to_owner(db, place)
    return PlaceOwnerView(**data).model_dump()
