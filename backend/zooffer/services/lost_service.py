from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from zooffer.core.errors import ForbiddenError, NotFoundError, ValidationAppError
from zooffer.db.models import Animal, LostReport, LostSighting, Profile
from zooffer.schemas.lost import (
    LostReportCreateRequest,
    LostReportUpdateRequest,
    LostSightingCreateRequest,
)
from zooffer.services import notification_service

EARTH_RADIUS_KM = 6371.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


async def _get_report(db: AsyncSession, public_id: UUID) -> LostReport:
    report = await db.scalar(select(LostReport).where(LostReport.public_id == public_id))
    if report is None:
        raise NotFoundError("Объявление о потере не найдено", code="lost_report_not_found")
    return report


async def _owner_display_name(db: AsyncSession, user_id: UUID) -> str | None:
    profile = await db.get(Profile, user_id)
    if profile is None:
        return None
    first = profile.public_first_name
    last = profile.public_last_name
    if first and last:
        return f"{first} {last}"
    return first or last


async def create_report(db: AsyncSession, user, payload: LostReportCreateRequest) -> LostReport:
    animal = None
    if payload.animal_id is not None:
        animal = await db.scalar(
            select(Animal).where(Animal.public_id == payload.animal_id, Animal.owner_id == user.id)
        )
        if animal is None:
            raise NotFoundError("Питомец не найден", code="animal_not_found")
        if animal.archived_at is not None:
            raise ValidationAppError("Питомец архивирован", code="animal_archived")
    lat = payload.last_seen_latitude
    lon = payload.last_seen_longitude
    if (lat is None) != (lon is None):
        raise ValidationAppError("Укажите обе координаты", code="invalid_coordinates")
    report = LostReport(
        id=uuid.uuid4(),
        public_id=uuid.uuid4(),
        reporter_id=user.id,
        animal_id=animal.id if animal is not None else None,
        status="searching",
        title=payload.title.strip(),
        description=payload.description.strip(),
        last_seen_at=payload.last_seen_at,
        last_seen_latitude=lat,
        last_seen_longitude=lon,
        last_seen_description=payload.last_seen_description,
        radius_km=payload.radius_km,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def get_report(db: AsyncSession, public_id: UUID) -> LostReport:
    return await _get_report(db, public_id)


async def update_report(
    db: AsyncSession, user, public_id: UUID, payload: LostReportUpdateRequest
) -> LostReport:
    report = await _get_report(db, public_id)
    if report.reporter_id != user.id:
        raise ForbiddenError("Нет прав на изменение", code="forbidden")
    if report.status == "closed":
        raise ValidationAppError("Объявление закрыто", code="report_closed")
    if payload.title is not None:
        report.title = payload.title.strip()
    if payload.description is not None:
        report.description = payload.description.strip()
    if payload.last_seen_at is not None:
        report.last_seen_at = payload.last_seen_at
    if payload.last_seen_latitude is not None or payload.last_seen_longitude is not None:
        lat = (
            payload.last_seen_latitude
            if payload.last_seen_latitude is not None
            else report.last_seen_latitude
        )
        lon = (
            payload.last_seen_longitude
            if payload.last_seen_longitude is not None
            else report.last_seen_longitude
        )
        if (lat is None) != (lon is None):
            raise ValidationAppError("Укажите обе координаты", code="invalid_coordinates")
        report.last_seen_latitude = lat
        report.last_seen_longitude = lon
    if payload.last_seen_description is not None:
        report.last_seen_description = payload.last_seen_description
    if payload.radius_km is not None:
        report.radius_km = payload.radius_km
    if payload.status is not None:
        if payload.status not in {"searching", "found", "closed"}:
            raise ValidationAppError("Некорректный статус", code="invalid_status")
        report.status = payload.status
        if payload.status == "found" and report.found_at is None:
            report.found_at = datetime.now(UTC)
        if payload.status == "closed" and report.closed_at is None:
            report.closed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(report)
    return report


async def close_report(db: AsyncSession, user, public_id: UUID) -> LostReport:
    report = await _get_report(db, public_id)
    if report.reporter_id != user.id:
        raise ForbiddenError("Нет прав на закрытие", code="forbidden")
    report.status = "closed"
    if report.closed_at is None:
        report.closed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(report)
    return report


async def list_reports(
    db: AsyncSession,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
    radius_km: float | None = None,
    status: str = "searching",
    limit: int = 50,
) -> list[LostReport]:
    query = select(LostReport).where(LostReport.status == status)
    reports = (await db.scalars(query)).all()
    if latitude is not None and longitude is not None and radius_km is not None:
        filtered = []
        for r in reports:
            if r.last_seen_latitude is None or r.last_seen_longitude is None:
                continue
            dist = _haversine_km(
                latitude, longitude, float(r.last_seen_latitude), float(r.last_seen_longitude)
            )
            if dist <= radius_km:
                filtered.append(r)
        reports = filtered
    reports = sorted(reports, key=lambda r: r.created_at, reverse=True)
    return list(reports[:limit])


async def add_sighting(
    db: AsyncSession, user, public_id: UUID, payload: LostSightingCreateRequest
) -> tuple[LostSighting, bool]:
    report = await _get_report(db, public_id)
    if report.status == "closed":
        raise ValidationAppError("Объявление закрыто", code="report_closed")
    # idempotency
    if payload.request_id:
        existing = await db.scalar(
            select(LostSighting).where(
                LostSighting.report_id == report.id,
                LostSighting.reporter_id == user.id,
                LostSighting.request_id == payload.request_id,
            )
        )
        if existing is not None:
            return existing, True
    sighting = LostSighting(
        id=uuid.uuid4(),
        report_id=report.id,
        reporter_id=user.id,
        request_id=payload.request_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        notes=payload.notes,
        seen_at=payload.seen_at,
    )
    db.add(sighting)
    # notify owner
    notification_service.create_notification(
        db,
        report.reporter_id,
        category="lost_pet",
        title="Новое свидетельство о питомце",
        body=(payload.notes or "Кто-то сообщил о местонахождении вашего питомца.")[:600],
        data={"lost_report_public_id": str(report.public_id)},
    )
    await db.commit()
    await db.refresh(sighting)
    return sighting, False


async def list_sightings(db: AsyncSession, public_id: UUID) -> list[LostSighting]:
    report = await _get_report(db, public_id)
    sightings = (
        await db.scalars(
            select(LostSighting)
            .where(LostSighting.report_id == report.id)
            .order_by(LostSighting.created_at.desc())
        )
    ).all()
    return list(sightings)


async def animal_name_for(db: AsyncSession, report: LostReport) -> tuple[str | None, str | None]:
    if report.animal_id is None:
        return None, None
    animal = await db.get(Animal, report.animal_id)
    if animal is None:
        return None, None
    return animal.name, animal.species


async def report_to_public(db: AsyncSession, report: LostReport) -> dict:
    name, species = await animal_name_for(db, report)
    owner_name = await _owner_display_name(db, report.reporter_id)
    return {
        "public_id": report.public_id,
        "status": report.status,
        "title": report.title,
        "description": report.description,
        "last_seen_at": report.last_seen_at,
        "last_seen_latitude": float(report.last_seen_latitude)
        if report.last_seen_latitude is not None
        else None,
        "last_seen_longitude": float(report.last_seen_longitude)
        if report.last_seen_longitude is not None
        else None,
        "last_seen_description": report.last_seen_description,
        "radius_km": report.radius_km,
        "found_at": report.found_at,
        "closed_at": report.closed_at,
        "created_at": report.created_at,
        "animal_name": name,
        "species": species,
        "owner": {"display_name": owner_name},
    }


async def report_to_owner(db: AsyncSession, report: LostReport) -> dict:
    return {
        "public_id": report.public_id,
        "status": report.status,
        "title": report.title,
        "description": report.description,
        "last_seen_at": report.last_seen_at,
        "last_seen_latitude": float(report.last_seen_latitude)
        if report.last_seen_latitude is not None
        else None,
        "last_seen_longitude": float(report.last_seen_longitude)
        if report.last_seen_longitude is not None
        else None,
        "last_seen_description": report.last_seen_description,
        "radius_km": report.radius_km,
        "found_at": report.found_at,
        "closed_at": report.closed_at,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
        "animal_id": None,
    }
