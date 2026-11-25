from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EventCreateRequest(StrictModel):
    event_type: str
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(default="", max_length=4000)
    city_id: int | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    location: str | None = Field(default=None, max_length=200)
    capacity: int | None = Field(default=None, ge=1)


class EventUpdateRequest(StrictModel):
    event_type: str | None = None
    title: str | None = Field(default=None, min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    city_id: int | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    location: str | None = Field(default=None, max_length=200)
    capacity: int | None = Field(default=None, ge=1)
    status: str | None = None


class PublicEventOwnerView(BaseModel):
    display_name: str | None = None


class PublicEventView(BaseModel):
    public_id: UUID
    event_type: str
    title: str
    description: str
    city_id: int | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    location: str | None = None
    capacity: int | None = None
    status: str
    created_at: datetime
    organizer: PublicEventOwnerView


class EventOwnerView(BaseModel):
    public_id: UUID
    event_type: str
    status: str
    title: str
    description: str
    city_id: int | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    location: str | None = None
    capacity: int | None = None
    created_at: datetime
    updated_at: datetime


class EventListResponse(BaseModel):
    items: list[PublicEventView]
    meta: dict[str, Any] = Field(default_factory=dict)
