from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from zooffer.api.deps import CurrentAuth, DbSession
from zooffer.db.models import Animal
from zooffer.schemas.lost import (
    LostReportCreateRequest,
    LostReportListResponse,
    LostReportOwnerView,
    LostReportUpdateRequest,
    LostSightingCreateRequest,
    LostSightingListResponse,
    LostSightingView,
    PublicLostReportView,
)
from zooffer.services import lost_service

router = APIRouter(prefix="/lost", tags=["lost"])


@router.post("", status_code=201)
async def create_lost_report(
    payload: LostReportCreateRequest,
    auth: CurrentAuth,
    db: DbSession,
) -> dict:
    user = auth.user
    report = await lost_service.create_report(db, user, payload)
    return await _owner_payload(db, report)


@router.get("")
async def list_lost_reports(
    db: DbSession,
    latitude: float | None = Query(default=None),
    longitude: float | None = Query(default=None),
    radius_km: float | None = Query(default=None),
    status: str = Query(default="searching"),
    limit: int = Query(default=50, le=200),
) -> LostReportListResponse:
    reports = await lost_service.list_reports(
        db, latitude=latitude, longitude=longitude, radius_km=radius_km, status=status, limit=limit
    )
    items = []
    for r in reports:
        pub = await lost_service.report_to_public(db, r)
        items.append(PublicLostReportView(**pub))
    return LostReportListResponse(items=items, meta={"total": len(items)})


@router.get("/{public_id}")
async def get_lost_report(public_id: uuid.UUID, db: DbSession) -> PublicLostReportView:
    report = await lost_service.get_report(db, public_id)
    pub = await lost_service.report_to_public(db, report)
    return PublicLostReportView(**pub)


@router.patch("/{public_id}")
async def update_lost_report(
    public_id: uuid.UUID,
    payload: LostReportUpdateRequest,
    auth: CurrentAuth,
    db: DbSession,
) -> dict:
    user = auth.user
    report = await lost_service.update_report(db, user, public_id, payload)
    return await _owner_payload(db, report)


@router.post("/{public_id}/close")
async def close_lost_report(
    public_id: uuid.UUID,
    auth: CurrentAuth,
    db: DbSession,
) -> dict:
    user = auth.user
    report = await lost_service.close_report(db, user, public_id)
    return await _owner_payload(db, report)


@router.post("/{public_id}/sightings", status_code=201)
async def add_sighting(
    public_id: uuid.UUID,
    payload: LostSightingCreateRequest,
    auth: CurrentAuth,
    db: DbSession,
) -> dict:
    user = auth.user
    sighting, idempotent = await lost_service.add_sighting(db, user, public_id, payload)
    return {
        "id": sighting.id,
        "latitude": float(sighting.latitude),
        "longitude": float(sighting.longitude),
        "notes": sighting.notes,
        "seen_at": sighting.seen_at,
        "created_at": sighting.created_at,
        "idempotent": idempotent,
    }


@router.get("/{public_id}/sightings")
async def list_sightings(public_id: uuid.UUID, db: DbSession) -> LostSightingListResponse:
    sightings = await lost_service.list_sightings(db, public_id)
    items = [
        LostSightingView(
            id=s.id,
            latitude=float(s.latitude),
            longitude=float(s.longitude),
            notes=s.notes,
            seen_at=s.seen_at,
            created_at=s.created_at,
        )
        for s in sightings
    ]
    return LostSightingListResponse(items=items)


async def _owner_payload(db: DbSession, report) -> dict:

    animal_public_id = None
    if report.animal_id is not None:
        animal = await db.get(Animal, report.animal_id)
        if animal is not None:
            animal_public_id = animal.public_id
    return LostReportOwnerView(
        public_id=report.public_id,
        status=report.status,
        title=report.title,
        description=report.description,
        last_seen_at=report.last_seen_at,
        last_seen_latitude=float(report.last_seen_latitude)
        if report.last_seen_latitude is not None
        else None,
        last_seen_longitude=float(report.last_seen_longitude)
        if report.last_seen_longitude is not None
        else None,
        last_seen_description=report.last_seen_description,
        radius_km=report.radius_km,
        found_at=report.found_at,
        closed_at=report.closed_at,
        created_at=report.created_at,
        updated_at=report.updated_at,
        animal_id=animal_public_id,
    ).model_dump()
