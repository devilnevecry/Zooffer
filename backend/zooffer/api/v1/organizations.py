from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from zooffer.api.deps import CurrentAuth, DbSession, OptionalAuth
from zooffer.core.errors import ForbiddenError
from zooffer.schemas.organization import (
    OrganizationCreateRequest,
    OrganizationListResponse,
    OrganizationOwnerView,
    OrganizationUpdateRequest,
    PublicOrganizationView,
)
from zooffer.services import organization_service

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", status_code=201)
async def create_organization(
    payload: OrganizationCreateRequest, auth: CurrentAuth, db: DbSession
) -> dict:
    user = auth.user
    org = await organization_service.create_organization(db, user, payload)
    return await _owner_payload(db, org)


@router.get("")
async def list_organizations(
    db: DbSession,
    auth: OptionalAuth = None,
    org_type: str | None = Query(default=None),
    city_id: int | None = Query(default=None),
    status: str = Query(default="approved"),
    limit: int = Query(default=50, le=200),
) -> OrganizationListResponse:
    if status != "approved" and (
        auth is None or getattr(auth.user, "role", None) not in {"admin", "superadmin"}
    ):
        raise ForbiddenError("Недостаточно прав", code="permission_denied")
    orgs = await organization_service.list_organizations(
        db, org_type=org_type, city_id=city_id, status=status, limit=limit
    )
    items = [
        PublicOrganizationView(**await organization_service.org_to_public(db, o)) for o in orgs
    ]
    return OrganizationListResponse(items=items, meta={"total": len(items)})


@router.get("/{public_id}")
async def get_organization(public_id: uuid.UUID, db: DbSession) -> PublicOrganizationView:
    org = await organization_service.get_organization(db, public_id)
    return PublicOrganizationView(**await organization_service.org_to_public(db, org))


@router.patch("/{public_id}")
async def update_organization(
    public_id: uuid.UUID, payload: OrganizationUpdateRequest, auth: CurrentAuth, db: DbSession
) -> dict:
    user = auth.user
    org = await organization_service.update_organization(db, user, public_id, payload)
    return await _owner_payload(db, org)


@router.post("/{public_id}/verify")
async def verify_organization(public_id: uuid.UUID, auth: CurrentAuth, db: DbSession) -> dict:
    user = auth.user
    org = await organization_service.verify_organization(db, user, public_id)
    return await _owner_payload(db, org)


async def _owner_payload(db, org) -> dict:
    data = await organization_service.org_to_owner(db, org)
    return OrganizationOwnerView(**data).model_dump()
