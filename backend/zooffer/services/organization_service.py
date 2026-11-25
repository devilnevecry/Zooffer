from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from zooffer.core.errors import ForbiddenError, NotFoundError, ValidationAppError
from zooffer.db.models import Organization, Profile

ORGTYPES = {"shelter", "kennel", "breeder", "clinic"}


async def _get(db, public_id):
    o = await db.scalar(select(Organization).where(Organization.public_id == public_id))
    if o is None:
        raise NotFoundError("Организация не найдена", code="organization_not_found")
    return o


async def _owner_name(db, user_id):
    profile = await db.get(Profile, user_id)
    if profile is None:
        return None
    first = profile.public_first_name
    last = profile.public_last_name
    if first and last:
        return f"{first} {last}"
    return first or last


async def create_organization(db, user, payload) -> Organization:
    if payload.org_type not in ORGTYPES:
        raise ValidationAppError("Некорректный тип", code="invalid_type")
    org = Organization(
        id=uuid.uuid4(),
        public_id=uuid.uuid4(),
        owner_id=user.id,
        org_type=payload.org_type,
        name=payload.name.strip(),
        description=payload.description.strip(),
        city_id=payload.city_id,
        status="pending",
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


async def update_organization(db, user, public_id, payload) -> Organization:
    org = await _get(db, public_id)
    if org.owner_id != user.id:
        raise ForbiddenError("Нет прав", code="forbidden")
    if payload.org_type is not None:
        if payload.org_type not in ORGTYPES:
            raise ValidationAppError("Некорректный тип", code="invalid_type")
        org.org_type = payload.org_type
    if payload.name is not None:
        org.name = payload.name.strip()
    if payload.description is not None:
        org.description = payload.description.strip()
    if payload.city_id is not None:
        org.city_id = payload.city_id
    await db.commit()
    await db.refresh(org)
    return org


async def verify_organization(db, user, public_id) -> Organization:
    if getattr(user, "role", None) not in {"admin", "superadmin"}:
        raise ForbiddenError("Недостаточно прав", code="permission_denied")
    org = await _get(db, public_id)
    org.verified = True
    org.verified_at = datetime.now(UTC)
    org.status = "approved"
    await db.commit()
    await db.refresh(org)
    return org


async def list_organizations(db, *, org_type=None, city_id=None, status="approved", limit=50):
    q = select(Organization).where(Organization.status == status)
    if org_type:
        q = q.where(Organization.org_type == org_type)
    if city_id is not None:
        q = q.where(Organization.city_id == city_id)
    rows = (await db.scalars(q)).all()
    rows = sorted(rows, key=lambda r: r.created_at, reverse=True)
    return list(rows[:limit])


async def get_organization(db, public_id):
    return await _get(db, public_id)


async def org_to_public(db, org) -> dict:
    return {
        "public_id": org.public_id,
        "org_type": org.org_type,
        "name": org.name,
        "description": org.description,
        "city_id": org.city_id,
        "verified": org.verified,
        "created_at": org.created_at,
        "owner": {"display_name": await _owner_name(db, org.owner_id)},
    }


async def org_to_owner(db, org) -> dict:
    return {
        "public_id": org.public_id,
        "org_type": org.org_type,
        "status": org.status,
        "name": org.name,
        "description": org.description,
        "city_id": org.city_id,
        "verified": org.verified,
        "created_at": org.created_at,
        "updated_at": org.updated_at,
    }
