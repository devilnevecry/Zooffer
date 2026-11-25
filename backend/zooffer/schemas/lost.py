from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LostReportCreateRequest(StrictModel):
    animal_id: UUID | None = None
    title: str = Field(min_length=3, max_length=140)
    description: str = Field(default="", max_length=2000)
    last_seen_at: datetime | None = None
    last_seen_latitude: Decimal | None = None
    last_seen_longitude: Decimal | None = None
    last_seen_description: str | None = Field(default=None, max_length=400)
    radius_km: int = Field(default=5, ge=1, le=100)


class LostReportUpdateRequest(StrictModel):
    title: str | None = Field(default=None, min_length=3, max_length=140)
    description: str | None = Field(default=None, max_length=2000)
    last_seen_at: datetime | None = None
    last_seen_latitude: Decimal | None = None
    last_seen_longitude: Decimal | None = None
    last_seen_description: str | None = Field(default=None, max_length=400)
    radius_km: int | None = Field(default=None, ge=1, le=100)
    status: str | None = None


class LostSightingCreateRequest(StrictModel):
    latitude: Decimal
    longitude: Decimal
    notes: str | None = Field(default=None, max_length=400)
    seen_at: datetime | None = None
    request_id: str | None = Field(default=None, max_length=64)


class PublicLostReportOwnerView(BaseModel):
    display_name: str | None = None


class PublicLostReportView(BaseModel):
    public_id: UUID
    status: str
    title: str
    description: str
    last_seen_at: datetime | None = None
    last_seen_latitude: float | None = None
    last_seen_longitude: float | None = None
    last_seen_description: str | None = None
    radius_km: int
    found_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime
    animal_name: str | None = None
    species: str | None = None
    owner: PublicLostReportOwnerView


class LostReportOwnerView(BaseModel):
    public_id: UUID
    status: str
    title: str
    description: str
    last_seen_at: datetime | None = None
    last_seen_latitude: float | None = None
    last_seen_longitude: float | None = None
    last_seen_description: str | None = None
    radius_km: int
    found_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    animal_id: UUID | None = None


class LostSightingView(BaseModel):
    id: UUID
    latitude: float
    longitude: float
    notes: str | None = None
    seen_at: datetime | None = None
    created_at: datetime


class LostReportListResponse(BaseModel):
    items: list[PublicLostReportView]
    meta: dict[str, Any] = Field(default_factory=dict)


class LostSightingListResponse(BaseModel):
    items: list[LostSightingView]
