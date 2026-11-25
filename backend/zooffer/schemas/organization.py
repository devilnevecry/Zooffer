from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OrganizationCreateRequest(StrictModel):
    org_type: str
    name: str = Field(min_length=2, max_length=140)
    description: str = Field(default="", max_length=4000)
    city_id: int | None = None


class OrganizationUpdateRequest(StrictModel):
    org_type: str | None = None
    name: str | None = Field(default=None, min_length=2, max_length=140)
    description: str | None = Field(default=None, max_length=4000)
    city_id: int | None = None


class PublicOrganizationOwnerView(BaseModel):
    display_name: str | None = None


class PublicOrganizationView(BaseModel):
    public_id: UUID
    org_type: str
    name: str
    description: str
    city_id: int | None = None
    verified: bool = False
    created_at: datetime
    owner: PublicOrganizationOwnerView


class OrganizationOwnerView(BaseModel):
    public_id: UUID
    org_type: str
    status: str
    name: str
    description: str
    city_id: int | None = None
    verified: bool = False
    created_at: datetime
    updated_at: datetime


class OrganizationListResponse(BaseModel):
    items: list[PublicOrganizationView]
    meta: dict[str, Any] = Field(default_factory=dict)
