from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlaceCreateRequest(StrictModel):
    category: str
    name: str = Field(min_length=2, max_length=140)
    description: str = Field(default="", max_length=2000)
    latitude: Decimal
    longitude: Decimal
    city_id: int | None = None


class PlaceUpdateRequest(StrictModel):
    category: str | None = None
    name: str | None = Field(default=None, min_length=2, max_length=140)
    description: str | None = Field(default=None, max_length=2000)
    latitude: Decimal | None = None
    longitude: Decimal | None = None


class PlaceModerateRequest(StrictModel):
    decision: str  # approve | reject
    reason: str | None = Field(default=None, max_length=400)


class PublicPlaceOwnerView(BaseModel):
    display_name: str | None = None


class PublicPlaceView(BaseModel):
    public_id: UUID
    category: str
    name: str
    description: str
    latitude: float
    longitude: float
    city_id: int | None = None
    created_at: datetime
    owner: PublicPlaceOwnerView


class PlaceOwnerView(BaseModel):
    public_id: UUID
    category: str
    status: str
    name: str
    description: str
    latitude: float
    longitude: float
    city_id: int | None = None
    moderation_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class PlaceListResponse(BaseModel):
    items: list[PublicPlaceView]
    meta: dict[str, Any] = Field(default_factory=dict)
